"""
Data cleaning and normalization for YouTube comments.

Cleans and normalizes comment content.
"""

import logging
import re
import html
import unicodedata
from typing import List

from src.core.models import Comment
from src.core.exceptions import DataCleaningError

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Cleans and normalizes comment content.
    """

    def __init__(self):
        """Initialize cleaner."""
        logger.info("[DataCleaner] Initialized")

    def clean_comments(self, comments: List[Comment]) -> List[Comment]:
        """
        Clean and normalize all comments.

        Args:
            comments: List of comments to clean

        Returns:
            List of comments with cleaned_content populated
        """
        logger.info(f"[DataCleaner] Cleaning {len(comments)} comments")

        cleaned_count = 0
        failed_count = 0

        for comment in comments:
            try:
                cleaned = self.normalize_text(comment.content)
                comment.cleaned_content = cleaned
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"[DataCleaner] Failed to clean comment {comment.id}: {e}")
                comment.cleaned_content = comment.content
                failed_count += 1

        logger.info(
            f"[DataCleaner] Cleaned {cleaned_count} comments, "
            f"Failed: {failed_count}"
        )

        return comments

    def detect_and_remove_spam(self, comments: List[Comment]) -> List[Comment]:
        """
        Identify and mark spam comments.

        Args:
            comments: List of comments

        Returns:
            List of non-spam comments
        """
        logger.info(f"[DataCleaner] Detecting spam in {len(comments)} comments")

        non_spam = []
        spam_count = 0

        for comment in comments:
            is_spam = self._is_spam(comment.cleaned_content)
            if is_spam:
                comment.metadata['is_spam'] = True
                spam_count += 1
            else:
                non_spam.append(comment)

        logger.info(f"[DataCleaner] Detected {spam_count} spam comments")
        return non_spam

    def normalize_text(self, text: str) -> str:
        """
        Normalize text: remove HTML, fix encoding, trim whitespace.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Decode HTML entities
        text = html.unescape(text)

        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)

        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        # Fix multiple whitespace
        text = re.sub(r'\s+', ' ', text)

        # Trim
        text = text.strip()

        return text

    def _is_spam(self, text: str) -> bool:
        """
        Check if text appears to be spam.

        Args:
            text: Text to check

        Returns:
            True if likely spam
        """
        if not text or len(text) < 3:
            return True

        # Check for excessive repeated characters
        if re.search(r'(.)\1{10,}', text):
            return True

        # Check for all caps with length > 50
        if len(text) > 50 and text.isupper():
            return True

        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', text)) / len(text)
        if special_char_ratio > 0.5:
            return True

        return False
