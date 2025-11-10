"""
Data validation for YouTube comments.

Validates loaded data for completeness and correctness.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from src.core.models import Comment
from src.core.exceptions import ValidationError
from src.utils.helpers import validate_url

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: str  # 'error', 'warning', 'info'
    comment_id: str
    field: str
    description: str


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    total_comments: int
    issues_found: List[ValidationIssue]
    recommendations: List[str]


class DataValidator:
    """
    Validates loaded data for completeness and correctness.
    """

    def __init__(self):
        """Initialize validator."""
        logger.info("[DataValidator] Initialized")

    def validate_comments(self, comments: List[Comment]) -> ValidationResult:
        """
        Check for required fields and data quality issues.

        Args:
            comments: List of comments to validate

        Returns:
            ValidationResult with issues found
        """
        logger.info(f"[DataValidator] Validating {len(comments)} comments")

        issues = []
        seen_ids = set()

        for comment in comments:
            # Check required fields
            if not comment.id:
                issues.append(ValidationIssue(
                    severity='error',
                    comment_id='unknown',
                    field='id',
                    description='Missing comment ID'
                ))

            # Check for duplicates
            if comment.id in seen_ids:
                issues.append(ValidationIssue(
                    severity='warning',
                    comment_id=comment.id,
                    field='id',
                    description='Duplicate comment ID'
                ))
            seen_ids.add(comment.id)

            # Check content
            if not comment.content or not comment.content.strip():
                issues.append(ValidationIssue(
                    severity='error',
                    comment_id=comment.id,
                    field='content',
                    description='Empty or null content'
                ))

            # Check parent_id
            if not comment.parent_id:
                issues.append(ValidationIssue(
                    severity='error',
                    comment_id=comment.id,
                    field='parent_id',
                    description='Missing parent_id'
                ))

            # Check URL format
            if not validate_url(comment.url):
                issues.append(ValidationIssue(
                    severity='warning',
                    comment_id=comment.id,
                    field='url',
                    description='Invalid YouTube URL format'
                ))

        # Generate recommendations
        recommendations = []
        error_count = sum(1 for i in issues if i.severity == 'error')
        warning_count = sum(1 for i in issues if i.severity == 'warning')

        if error_count > 0:
            recommendations.append(f"Fix {error_count} critical errors before processing")
        if warning_count > 0:
            recommendations.append(f"Review {warning_count} warnings for data quality")

        is_valid = error_count == 0

        logger.info(
            f"[DataValidator] Validation complete - "
            f"Valid: {is_valid}, Errors: {error_count}, Warnings: {warning_count}"
        )

        return ValidationResult(
            is_valid=is_valid,
            total_comments=len(comments),
            issues_found=issues,
            recommendations=recommendations
        )

    def fix_recoverable_issues(self, comments: List[Comment]) -> List[Comment]:
        """
        Fix recoverable issues like duplicates and whitespace.

        Args:
            comments: List of comments to fix

        Returns:
            List of cleaned comments
        """
        logger.info(f"[DataValidator] Fixing recoverable issues in {len(comments)} comments")

        # Remove duplicates (keep first occurrence)
        seen_ids = set()
        unique_comments = []
        duplicates = 0

        for comment in comments:
            if comment.id not in seen_ids:
                # Strip whitespace
                comment.content = comment.content.strip()
                comment.id = comment.id.strip()
                comment.parent_id = comment.parent_id.strip()

                unique_comments.append(comment)
                seen_ids.add(comment.id)
            else:
                duplicates += 1

        logger.info(
            f"[DataValidator] Fixed issues - "
            f"Removed {duplicates} duplicates, "
            f"Kept {len(unique_comments)} unique comments"
        )

        return unique_comments
