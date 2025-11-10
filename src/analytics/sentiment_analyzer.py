"""
Sentiment analysis for comments.

Analyzes comment sentiment using LLM.
"""

import logging
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.core.models import Comment
from src.ai.openai_client import OpenAIClient
from src.ai.prompts import Prompts
from src.utils.helpers import batch_list
from config import Config

import re

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    overall_score: float
    distribution: Dict[str, int]
    comment_scores: Dict[str, float]
    confidence: float


class SentimentAnalyzer:
    """
    Performs sentiment analysis on comments.
    """
    def _extract_json_array(self, text: str) -> Optional[List[float]]:
        """
        Extract JSON array from response text.

        Handles cases where model returns text before/after JSON.

        Args:
            text: Response text from model

        Returns:
            List of floats if found, None otherwise
        """
        import re
        
        # Try to find JSON array pattern
        json_match = re.search(r'\[[\d.,\s]+\]', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try direct parse
        text = text.strip()
        if text.startswith('[') and text.endswith(']'):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        
        return None

    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize sentiment analyzer.

        Args:
            openai_client: OpenAI client for API calls
        """
        self.openai_client = openai_client
        self.prompts = Prompts()
        logger.info("[SentimentAnalyzer] Initialized")

    def analyze_sentiment(
        self,
        comments: List[Comment],
        batch_size: Optional[int] = None
    ) -> SentimentResult:
        """
        Analyzes sentiment for all comments.

        Args:
            comments: List of Comment objects to analyze
            batch_size: Optional batch size for processing

        Returns:
            SentimentResult with overall statistics
        """
        batch_size = batch_size or Config.BATCH_SIZE
        logger.info(f"[SentimentAnalyzer] Analyzing {len(comments)} comments")

        all_scores = {}
        batches = batch_list(comments, batch_size)

        for i, batch in enumerate(batches, 1):
            logger.info(f"[SentimentAnalyzer] Processing batch {i}/{len(batches)}")

            try:
                scores = self._analyze_batch(batch)
                for comment, score in zip(batch, scores):
                    all_scores[comment.id] = score
            except Exception as e:
                logger.error(f"[SentimentAnalyzer] Batch {i} failed: {e}")
                # Assign neutral scores for failed batch
                for comment in batch:
                    all_scores[comment.id] = 0.5

        # Calculate statistics
        score_values = list(all_scores.values())
        overall_score = sum(score_values) / len(score_values) if score_values else 0.5

        # Distribution
        positive = sum(1 for s in score_values if s > 0.6)
        neutral = sum(1 for s in score_values if 0.4 <= s <= 0.6)
        negative = sum(1 for s in score_values if s < 0.4)

        logger.info(
            f"[SentimentAnalyzer] Analysis complete - "
            f"Overall: {overall_score:.2f}, Pos: {positive}, Neu: {neutral}, Neg: {negative}"
        )

        return SentimentResult(
            overall_score=overall_score,
            distribution={
                "positive": positive,
                "neutral": neutral,
                "negative": negative
            },
            comment_scores=all_scores,
            confidence=0.85  # Placeholder
        )

    def _analyze_batch(self, batch: List[Comment]) -> List[float]:
        """
        Analyzes sentiment for a batch of comments.

        Args:
            batch: Batch of comments

        Returns:
            List of sentiment scores
        """
        prompt = self.prompts.format_sentiment_prompt(batch)

        try:
            result = self.openai_client.create_completion(
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                model=Config.FAST_COMPLETION_MODEL
            )

            # Parse JSON array of scores
            scores = json.loads(result.content)

            # Ensure we have the right number of scores
            if len(scores) != len(batch):
                logger.warning(
                    f"[SentimentAnalyzer] Score count mismatch: "
                    f"expected {len(batch)}, got {len(scores)}"
                )
                # Pad or trim
                while len(scores) < len(batch):
                    scores.append(0.5)
                scores = scores[:len(batch)]

            return scores

        except Exception as e:
            logger.error(f"[SentimentAnalyzer] Failed to parse scores: {e}")
            # Return neutral scores
            return [0.5] * len(batch)
