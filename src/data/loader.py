"""
Module: src/data/loader.py
Purpose: Load and parse CSV data into Comment objects.
"""

import logging
from pathlib import Path
from typing import List

import pandas as pd

from src.core.models import Comment
from src.core.exceptions import DataException, FileNotFoundError, CSVParsingError
from config import Config

logger = logging.getLogger(__name__)


class CSVLoader:
    """
    Loads YouTube comments data from CSV file.

    Handles encoding issues and creates Comment objects from raw CSV data.
    """

    def __init__(self, config: Config):
        """
        Initialize CSV loader.

        Args:
            config: Configuration object with settings
        """
        self.config = config
        logger.info("[CSVLoader] Initialized")

    def load_csv(self, file_path: str) -> List[Comment]:
        """
        Load comments from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of Comment objects

        Raises:
            FileNotFoundError: If file does not exist
            CSVParsingError: If CSV cannot be parsed
            DataException: For other data loading errors
        """
        logger.info(f"[CSVLoader] Loading CSV from {file_path}")

        # Validate file exists
        if not Path(file_path).exists():
            logger.error(f"[CSVLoader] File not found: {file_path}")
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Try UTF-8 first, fallback to latin-1
        encoding = 'utf-8'
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            logger.info(f"[CSVLoader] Loaded with {encoding} encoding")
        except UnicodeDecodeError:
            logger.warning(f"[CSVLoader] UTF-8 failed, trying latin-1")
            encoding = 'latin-1'
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"[CSVLoader] Loaded with {encoding} encoding")
            except Exception as e:
                logger.error(f"[CSVLoader] Failed to load CSV: {e}", exc_info=True)
                raise CSVParsingError(f"Could not parse CSV: {e}") from e
        except Exception as e:
            logger.error(f"[CSVLoader] Failed to load CSV: {e}", exc_info=True)
            raise DataException(f"Error loading CSV: {e}") from e

        # Validate required columns
        required_columns = ['id', 'url', 'content', 'author_id', 'parent_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"[CSVLoader] Missing columns: {missing_columns}")
            raise CSVParsingError(f"Missing required columns: {missing_columns}")

        # Convert to Comment objects
        comments = []
        for idx, row in df.iterrows():
            try:
                comment = Comment(
                    id=str(row['id']),
                    url=str(row['url']),
                    content=str(row['content']),
                    author_id=str(row['author_id']),
                    parent_id=str(row['parent_id'])
                )
                comments.append(comment)
            except Exception as e:
                logger.warning(f"[CSVLoader] Skipping row {idx}: {e}")
                continue

        logger.info(f"[CSVLoader] Loaded {len(comments)} comments from {len(df)} rows")
        return comments
