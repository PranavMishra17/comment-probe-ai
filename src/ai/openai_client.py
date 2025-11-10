"""
OpenAI API client wrapper with error handling and retry logic.

Provides robust API interaction with rate limiting, retries, and comprehensive logging.
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import openai
from openai import OpenAI, OpenAIError, RateLimitError as OpenAIRateLimitError, APIConnectionError as OpenAIAPIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.exceptions import AIException, RateLimitError, APIConnectionError, APIKeyError, InvalidResponseError
from src.utils.rate_limiter import RateLimiter
from src.utils.logger import get_openai_logger
from config import Config

logger = logging.getLogger(__name__)
api_logger = get_openai_logger()


@dataclass
class CompletionResult:
    """Result of a completion API call."""
    content: str
    model: str
    tokens_used: int
    cost_estimate: float
    response_time: float


class OpenAIClient:
    """
    Wrapper for OpenAI API with error handling and retry logic.
    """

    # Cost per 1K tokens (as of Jan 2025)
    COSTS = {
        'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
        'gpt-3.5-turbo': {'prompt': 0.0005, 'completion': 0.0015},
        'text-embedding-3-small': {'embedding': 0.00002}
    }

    def __init__(self, api_key: str, rate_limiter: RateLimiter):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            rate_limiter: Rate limiter instance

        Raises:
            APIKeyError: If API key is invalid
        """
        if not api_key or not api_key.startswith('sk-'):
            logger.error("[OpenAIClient] Invalid API key format")
            raise APIKeyError("Invalid OpenAI API key")

        self.client = OpenAI(api_key=api_key, timeout=Config.API_TIMEOUT)
        self.rate_limiter = rate_limiter
        logger.info("[OpenAIClient] Initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((OpenAIRateLimitError, OpenAIAPIConnectionError))
    )
    def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> CompletionResult:
        """
        Creates chat completion with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to Config.COMPLETION_MODEL)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            CompletionResult

        Raises:
            AIException: On API errors
        """
        model = model or Config.COMPLETION_MODEL
        temperature = temperature if temperature is not None else Config.COMPLETION_TEMPERATURE
        max_tokens = max_tokens or Config.COMPLETION_MAX_TOKENS

        # Estimate tokens for rate limiting
        prompt_text = ' '.join([m['content'] for m in messages])
        estimated_tokens = len(prompt_text) // 4 + max_tokens

        # Acquire rate limit
        self.rate_limiter.acquire(estimated_tokens)

        logger.info(f"[OpenAIClient] Creating completion with {model}")
        start_time = time.time()

        try:
            # Make API call
            kwargs = {
                'model': model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            if response_format:
                kwargs['response_format'] = response_format

            response = self.client.chat.completions.create(**kwargs)

            # Extract result
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            response_time = time.time() - start_time

            # Calculate cost
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

            # Log to openai_calls.log
            self._log_api_call(
                operation='create_completion',
                model=model,
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                cost=cost,
                duration_ms=int(response_time * 1000),
                status='success'
            )

            logger.info(
                f"[OpenAIClient] Completion successful - "
                f"Tokens: {tokens_used}, Cost: ${cost:.4f}, Time: {response_time:.2f}s"
            )

            return CompletionResult(
                content=content,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost,
                response_time=response_time
            )

        except OpenAIRateLimitError as e:
            logger.warning(f"[OpenAIClient] Rate limit hit: {e}")
            self._log_api_call(
                operation='create_completion',
                model=model,
                status='rate_limit_error'
            )
            raise RateLimitError(f"Rate limit exceeded: {e}") from e

        except OpenAIAPIConnectionError as e:
            logger.error(f"[OpenAIClient] Connection error: {e}")
            self._log_api_call(
                operation='create_completion',
                model=model,
                status='connection_error'
            )
            raise APIConnectionError(f"API connection failed: {e}") from e

        except OpenAIError as e:
            logger.error(f"[OpenAIClient] API error: {e}", exc_info=True)
            self._log_api_call(
                operation='create_completion',
                model=model,
                status='error'
            )
            raise AIException(f"OpenAI API error: {e}") from e

        except Exception as e:
            logger.error(f"[OpenAIClient] Unexpected error: {e}", exc_info=True)
            raise AIException(f"Unexpected error: {e}") from e

    def create_batch_completion(
        self,
        message_batches: List[List[Dict[str, str]]],
        model: Optional[str] = None
    ) -> List[CompletionResult]:
        """
        Creates multiple completions sequentially.

        Args:
            message_batches: List of message lists
            model: Model to use

        Returns:
            List of CompletionResults
        """
        logger.info(f"[OpenAIClient] Processing {len(message_batches)} completion batches")

        results = []
        for i, messages in enumerate(message_batches, 1):
            logger.info(f"[OpenAIClient] Batch {i}/{len(message_batches)}")
            try:
                result = self.create_completion(messages, model=model)
                results.append(result)
            except Exception as e:
                logger.error(f"[OpenAIClient] Batch {i} failed: {e}")
                # Continue with other batches
                continue

        logger.info(f"[OpenAIClient] Completed {len(results)}/{len(message_batches)} batches")
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((OpenAIRateLimitError, OpenAIAPIConnectionError))
    )
    def create_embedding(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generates embeddings for texts.

        Args:
            texts: List of texts to embed (max 100)
            model: Embedding model to use

        Returns:
            List of embedding vectors

        Raises:
            AIException: On API errors
        """
        model = model or Config.EMBEDDING_MODEL

        if len(texts) > 100:
            raise ValueError(f"Cannot embed more than 100 texts at once, got {len(texts)}")

        # Estimate tokens
        total_chars = sum(len(t) for t in texts)
        estimated_tokens = total_chars // 4

        # Acquire rate limit
        self.rate_limiter.acquire(estimated_tokens)

        logger.info(f"[OpenAIClient] Creating embeddings for {len(texts)} texts")
        start_time = time.time()

        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts,
                encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]
            tokens_used = response.usage.total_tokens
            response_time = time.time() - start_time

            cost = self._estimate_embedding_cost(model, tokens_used)

            # Log
            self._log_api_call(
                operation='create_embedding',
                model=model,
                tokens_prompt=tokens_used,
                tokens_completion=0,
                cost=cost,
                duration_ms=int(response_time * 1000),
                status='success'
            )

            logger.info(
                f"[OpenAIClient] Embeddings created - "
                f"Count: {len(embeddings)}, Tokens: {tokens_used}, "
                f"Cost: ${cost:.4f}, Time: {response_time:.2f}s"
            )

            return embeddings

        except OpenAIRateLimitError as e:
            logger.warning(f"[OpenAIClient] Rate limit hit: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e

        except OpenAIAPIConnectionError as e:
            logger.error(f"[OpenAIClient] Connection error: {e}")
            raise APIConnectionError(f"API connection failed: {e}") from e

        except OpenAIError as e:
            logger.error(f"[OpenAIClient] API error: {e}", exc_info=True)
            raise AIException(f"OpenAI API error: {e}") from e

        except Exception as e:
            logger.error(f"[OpenAIClient] Unexpected error: {e}", exc_info=True)
            raise AIException(f"Unexpected error: {e}") from e

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimates cost for completion."""
        if model not in self.COSTS:
            return 0.0

        costs = self.COSTS[model]
        prompt_cost = (prompt_tokens / 1000) * costs['prompt']
        completion_cost = (completion_tokens / 1000) * costs['completion']
        return prompt_cost + completion_cost

    def _estimate_embedding_cost(self, model: str, tokens: int) -> float:
        """Estimates cost for embeddings."""
        if model not in self.COSTS:
            return 0.0

        return (tokens / 1000) * self.COSTS[model]['embedding']

    def _log_api_call(
        self,
        operation: str,
        model: str,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        status: str = 'unknown'
    ) -> None:
        """Logs API call to openai_calls.log."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "model": model,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "tokens_total": tokens_prompt + tokens_completion,
            "cost_estimate": round(cost, 6),
            "duration_ms": duration_ms,
            "status": status
        }
        api_logger.info(json.dumps(log_entry))
