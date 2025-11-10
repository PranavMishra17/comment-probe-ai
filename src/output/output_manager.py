"""
Output management and coordination.

Orchestrates all output generation.
"""

import logging
import os
import shutil
from typing import List, Dict, Optional

from src.core.models import Video, AnalyticsResult, ProcessingMetadata
from src.output.results_writer import ResultsWriter
from src.utils.helpers import generate_run_id
from config import Config

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Orchestrates all output generation.
    """

    def __init__(self, base_output_dir: Optional[str] = None):
        """
        Initialize output manager.

        Args:
            base_output_dir: Base directory for outputs
        """
        self.base_output_dir = base_output_dir or Config.OUTPUT_BASE_DIR
        self.run_id = None
        self.run_dir = None
        self.results_writer = ResultsWriter()
        logger.info(f"[OutputManager] Initialized with base dir: {self.base_output_dir}")

    def create_run_directory(self) -> str:
        """
        Creates output directory for this run.

        Returns:
            Path to run directory
        """
        self.run_id = generate_run_id()
        self.run_dir = os.path.join(self.base_output_dir, f"run-{self.run_id}")

        logger.info(f"[OutputManager] Creating run directory: {self.run_dir}")

        try:
            # Create main directory
            os.makedirs(self.run_dir, exist_ok=True)

            # Create subdirectories
            os.makedirs(os.path.join(self.run_dir, "logs"), exist_ok=True)
            os.makedirs(os.path.join(self.run_dir, "visualization"), exist_ok=True)

            logger.info(f"[OutputManager] Run directory created: {self.run_dir}")
            return self.run_dir

        except Exception as e:
            logger.error(f"[OutputManager] Failed to create run directory: {e}", exc_info=True)
            raise

    def save_results(
        self,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> None:
        """
        Saves all results.

        Args:
            videos: List of videos
            analytics: Analytics results
            metadata: Processing metadata
        """
        logger.info("[OutputManager] Saving results")

        if not self.run_dir:
            self.create_run_directory()

        # Write results.json
        results_path = os.path.join(self.run_dir, Config.RESULTS_FILENAME)
        self.results_writer.write_results(results_path, videos, analytics, metadata)

        # Write metadata.json
        metadata_path = os.path.join(self.run_dir, Config.METADATA_FILENAME)
        metadata.save(metadata_path)

        logger.info("[OutputManager] Results saved successfully")

    def get_run_id(self) -> str:
        """
        Returns current run ID.

        Returns:
            Run ID
        """
        return self.run_id if self.run_id else "unknown"
