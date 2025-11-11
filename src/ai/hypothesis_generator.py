"""
Dynamic CommentSearchSpec generation for videos.

Generates video-specific search specs using LLM analysis.
"""

import logging
import json
from typing import List, Optional

from src.core.models import Video, CommentSearchSpec
from src.ai.openai_client import OpenAIClient
from src.ai.prompts import Prompts
from config import Config

logger = logging.getLogger(__name__)


class HypothesisGenerator:
    """
    Generates dynamic CommentSearchSpecs for each video.
    """

    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize hypothesis generator.

        Args:
            openai_client: OpenAI client for API calls
        """
        self.openai_client = openai_client
        self.prompts = Prompts()
        logger.info("[HypothesisGenerator] Initialized")

    def _extract_json_from_text(self, text: str) -> str:
        """
        Extracts clean JSON from potentially contaminated LLM response.

        Args:
            text: Raw LLM response text

        Returns:
            Cleaned JSON string

        Raises:
            ValueError: If no valid JSON found
        """
        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove common prefixes that LLMs add
        prefixes = [
            "Here is the JSON:",
            "Here's the JSON:",
            "The JSON is:",
            "JSON:",
            "```json",
            "```",
        ]
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # Remove common suffixes
        suffixes = ["```", "\n\n", "Let me know if you need anything else!", "Hope this helps!"]
        for suffix in suffixes:
            if text.endswith(suffix):
                text = text[:-len(suffix)].strip()

        # Find JSON boundaries (first { to last })
        start = text.find('{')
        end = text.rfind('}')

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No valid JSON object found in text")

        json_str = text[start:end+1]

        # Remove any trailing text after the closing brace
        # Sometimes LLMs add explanations after the JSON
        json_str = json_str.strip()

        return json_str

    def generate_search_specs(
        self,
        video: Video,
        num_specs: Optional[int] = None
    ) -> List[CommentSearchSpec]:
        """
        Generates dynamic search specs for a video.

        Args:
            video: Video to analyze
            num_specs: Number of specs to generate

        Returns:
            List of CommentSearchSpecs
        """
        num_specs = num_specs or Config.NUM_DYNAMIC_SPECS

        logger.info(f"[HypothesisGenerator] Generating {num_specs} specs for video {video.id}")

        # Sample diverse comments
        sample_comments = video.get_sample_comments(Config.SAMPLE_COMMENTS_FOR_HYPOTHESIS)

        # Create prompt
        prompt = self.prompts.format_hypothesis_prompt(video, sample_comments)

        try:
            # Call LLM
            result = self.openai_client.create_completion(
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing YouTube comments. Respond with ONLY valid JSON, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                model=Config.COMPLETION_MODEL,
                response_format={"type": "json_object"}
            )

            # Parse response with robust extraction
            content = result.content

            # Try direct parsing first
            try:
                specs_data = json.loads(content)
            except json.JSONDecodeError as e:
                # Clean and extract JSON from contaminated response
                logger.warning(f"[HypothesisGenerator] Direct JSON parse failed: {e}, attempting extraction")
                try:
                    cleaned_json = self._extract_json_from_text(content)
                    specs_data = json.loads(cleaned_json)
                    logger.info(f"[HypothesisGenerator] Successfully extracted JSON after cleaning")
                except Exception as extract_error:
                    logger.error(f"[HypothesisGenerator] JSON extraction failed: {extract_error}")
                    raise e  # Re-raise original error

            # Handle both array and object with array
            if isinstance(specs_data, list):
                specs_list = specs_data
            elif isinstance(specs_data, dict) and 'specs' in specs_data:
                specs_list = specs_data['specs']
            elif isinstance(specs_data, dict) and 'search_specs' in specs_data:
                specs_list = specs_data['search_specs']
            else:
                logger.warning(f"[HypothesisGenerator] Unexpected response format: {list(specs_data.keys())}, using fallback")
                return self._create_fallback_specs(num_specs)

            # Convert to CommentSearchSpec objects
            specs = []
            for spec_data in specs_list[:num_specs]:
                try:
                    spec = CommentSearchSpec(
                        query=spec_data.get('query', ''),
                        context=spec_data.get('context', 'generated'),
                        filters=spec_data.get('filters', {}),
                        extract_fields=spec_data.get('extract_fields', []),
                        is_static=False,
                        rationale=spec_data.get('rationale', ''),
                        top_k=30
                    )
                    specs.append(spec)
                except Exception as e:
                    logger.warning(f"[HypothesisGenerator] Failed to create spec: {e}")
                    continue

            logger.info(f"[HypothesisGenerator] Generated {len(specs)} specs successfully")
            return specs

        except Exception as e:
            logger.error(f"[HypothesisGenerator] Failed to generate specs: {e}", exc_info=True)
            # Return fallback specs
            return self._create_fallback_specs(num_specs)

    def _create_fallback_specs(self, num_specs: int) -> List[CommentSearchSpec]:
        """Creates generic fallback specs when LLM fails."""
        logger.info("[HypothesisGenerator] Creating fallback specs")

        fallback_specs = [
            CommentSearchSpec(
                query="Find comments with detailed feedback or suggestions",
                context="general_feedback",
                filters={},
                extract_fields=["sentiment", "suggestions"],
                is_static=False,
                rationale="General feedback is always valuable"
            ),
            CommentSearchSpec(
                query="Find questions about the content or topic",
                context="audience_questions",
                filters={"require_question_mark": True},
                extract_fields=["topics"],
                is_static=False,
                rationale="Questions reveal audience needs"
            ),
            CommentSearchSpec(
                query="Find comments mentioning issues or problems",
                context="issues_and_concerns",
                filters={},
                extract_fields=["sentiment", "issues"],
                is_static=False,
                rationale="Issues need attention"
            )
        ]

        return fallback_specs[:num_specs]
