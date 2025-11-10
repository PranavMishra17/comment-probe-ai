"""
Question identification and ranking.

Finds and ranks questions from comments.
"""

import logging
import json
import re
from typing import List, Optional

from src.core.models import Comment, Question
from src.ai.openai_client import OpenAIClient
from src.ai.prompts import Prompts
from config import Config

logger = logging.getLogger(__name__)


class QuestionFinder:
    """
    Identifies and ranks popular questions from comments.
    """

    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize question finder.

        Args:
            openai_client: OpenAI client for validation
        """
        self.openai_client = openai_client
        self.prompts = Prompts()
        logger.info("[QuestionFinder] Initialized")

    def find_top_questions(
        self,
        comments: List[Comment],
        top_n: Optional[int] = None
    ) -> List[Question]:
        """
        Finds top N questions from comments.

        Args:
            comments: List of comments
            top_n: Number of questions to return

        Returns:
            List of Question objects
        """
        top_n = top_n or Config.NUM_QUESTIONS
        logger.info(f"[QuestionFinder] Finding top {top_n} questions from {len(comments)} comments")

        # Stage 1: Filter comments with question marks
        potential_questions = self._filter_questions(comments)
        logger.info(f"[QuestionFinder] Found {len(potential_questions)} potential questions")

        if not potential_questions:
            return []

        # Stage 2: Rank by engagement
        ranked = sorted(
            potential_questions,
            key=lambda c: self._extract_engagement_score(c),
            reverse=True
        )

        # Stage 3: Validate and categorize (simplified - skip LLM validation)
        questions = []
        for comment in ranked[:top_n * 2]:  # Get more than needed
            question = Question(
                comment=comment,
                question_text=comment.cleaned_content,
                engagement_score=self._extract_engagement_score(comment),
                is_answered=False,
                category="general",
                relevance_score=0.8
            )
            questions.append(question)

        logger.info(f"[QuestionFinder] Identified {len(questions[:top_n])} questions")
        return questions[:top_n]

    def _filter_questions(self, comments: List[Comment]) -> List[Comment]:
        """
        Filters comments that appear to be questions.

        Args:
            comments: Comments to filter

        Returns:
            List of comments with questions
        """
        questions = []
        for comment in comments:
            # Check for question mark
            if '?' in comment.cleaned_content:
                # Check minimum length
                if len(comment.cleaned_content) > Config.MIN_COMMENT_LENGTH:
                    questions.append(comment)

        return questions

    def _extract_engagement_score(self, comment: Comment) -> float:
        """
        Extracts engagement score from comment metadata.

        Args:
            comment: Comment to score

        Returns:
            Engagement score
        """
        # Try to get from metadata
        likes = comment.metadata.get('likes', 0)
        replies = comment.metadata.get('replies', 0)

        # Simple formula
        score = likes * 1.0 + replies * 2.0

        return float(score)
