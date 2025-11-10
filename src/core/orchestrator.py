"""
Main workflow orchestrator.

Coordinates all components and executes the complete analysis pipeline.
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Tuple

from src.core.models import Comment, Video, AnalyticsResult, ProcessingMetadata, CommentSearchSpec
from src.data.loader import CSVLoader
from src.data.validator import DataValidator
from src.data.cleaner import DataCleaner
from src.data.video_discoverer import VideoDiscoverer
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.hypothesis_generator import HypothesisGenerator
from src.ai.search_engine import SearchEngine
from src.analytics.sentiment_analyzer import SentimentAnalyzer
from src.analytics.topic_extractor import TopicExtractor
from src.analytics.question_finder import QuestionFinder
from src.output.output_manager import OutputManager
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from config import Config

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main workflow controller that coordinates all components.
    """

    def __init__(self, config: Config):
        """
        Initialize orchestrator and all components.

        Args:
            config: Configuration object
        """
        self.config = config
        logger.info("[Orchestrator] Initializing components")

        # Initialize infrastructure
        self.cache_manager = CacheManager(config.CACHE_DIR)
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.REQUESTS_PER_MINUTE,
            tokens_per_minute=config.TOKENS_PER_MINUTE
        )

        # Initialize AI components
        self.openai_client = OpenAIClient(config.OPENAI_API_KEY, self.rate_limiter)
        self.embedder = Embedder(self.openai_client, self.cache_manager)
        self.hypothesis_generator = HypothesisGenerator(self.openai_client)
        self.search_engine = SearchEngine(self.openai_client, self.embedder)

        # Initialize data pipeline
        self.csv_loader = CSVLoader(config)
        self.validator = DataValidator()
        self.cleaner = DataCleaner()
        self.video_discoverer = VideoDiscoverer()

        # Initialize analytics
        self.sentiment_analyzer = SentimentAnalyzer(self.openai_client)
        self.topic_extractor = TopicExtractor(self.embedder, self.openai_client)
        self.question_finder = QuestionFinder(self.openai_client)

        # Initialize output
        self.output_manager = OutputManager(config.OUTPUT_BASE_DIR)

        logger.info("[Orchestrator] Initialization complete")

    def run_analysis(self, csv_path: str) -> str:
        """
        Main entry point for analysis.

        Executes complete workflow from CSV to outputs.

        Args:
            csv_path: Path to input CSV file

        Returns:
            Run ID

        Raises:
            Various exceptions on failures
        """
        logger.info(f"[Orchestrator] Starting analysis of {csv_path}")
        start_time = datetime.utcnow()

        # Create metadata
        metadata = ProcessingMetadata(
            run_id=self.output_manager.get_run_id(),
            start_time=start_time,
            input_file=csv_path
        )

        try:
            # Phase 1: Load and Validate Data
            comments = self._load_and_validate_data(csv_path)

            # Phase 2: Discover Videos
            videos, orphaned = self._discover_videos(comments)

            # Phase 3: Generate Embeddings
            self._generate_embeddings(videos)

            # Phase 4: Generate Search Specs
            self._generate_search_specs(videos)

            # Phase 5: Execute Searches
            search_results = self._execute_searches(videos)

            # Phase 6: Perform Analytics
            analytics = self._perform_analytics(videos, search_results)

            # Phase 7: Generate Outputs
            end_time = datetime.utcnow()
            metadata.end_time = end_time
            metadata.total_duration = (end_time - start_time).total_seconds()
            metadata.videos_processed = len(videos)
            metadata.total_comments = sum(len(v.comments) for v in videos)

            self._generate_outputs(videos, analytics, metadata)

            logger.info(f"[Orchestrator] Analysis complete - Run ID: {metadata.run_id}")
            return metadata.run_id

        except Exception as e:
            logger.error(f"[Orchestrator] Analysis failed: {e}", exc_info=True)
            raise

    def _load_and_validate_data(self, csv_path: str) -> List[Comment]:
        """Phase 1: Load, validate, and clean data."""
        logger.info("[Orchestrator] Phase 1: Loading and validating data")

        # Load CSV
        comments = self.csv_loader.load_csv(csv_path)

        # Validate
        validation_result = self.validator.validate_comments(comments)
        if not validation_result.is_valid:
            logger.warning(f"[Orchestrator] Validation issues: {len(validation_result.issues_found)}")

        # Fix recoverable issues
        comments = self.validator.fix_recoverable_issues(comments)

        # Clean
        comments = self.cleaner.clean_comments(comments)
        comments = self.cleaner.detect_and_remove_spam(comments)

        logger.info(f"[Orchestrator] Phase 1 complete - {len(comments)} comments")
        return comments

    def _discover_videos(self, comments: List[Comment]) -> Tuple[List[Video], List[Comment]]:
        """Phase 2: Discover videos and group comments."""
        logger.info("[Orchestrator] Phase 2: Discovering videos")

        videos, orphaned = self.video_discoverer.discover_videos(comments)
        self.video_discoverer.validate_discovery(videos)

        logger.info(f"[Orchestrator] Phase 2 complete - {len(videos)} videos")
        return videos, orphaned

    def _generate_embeddings(self, videos: List[Video]) -> None:
        """Phase 3: Generate embeddings for all comments."""
        logger.info("[Orchestrator] Phase 3: Generating embeddings")

        for i, video in enumerate(videos, 1):
            logger.info(f"[Orchestrator] Embedding video {i}/{len(videos)}")
            self.embedder.embed_comments(video.comments)

        logger.info("[Orchestrator] Phase 3 complete")

    def _generate_search_specs(self, videos: List[Video]) -> None:
        """Phase 4: Generate static and dynamic search specs."""
        logger.info("[Orchestrator] Phase 4: Generating search specs")

        # Static specs from config
        static_specs = [CommentSearchSpec.from_dict(spec) for spec in Config.STATIC_SEARCH_SPECS]

        for i, video in enumerate(videos, 1):
            logger.info(f"[Orchestrator] Generating specs for video {i}/{len(videos)}")

            video.static_search_specs = static_specs

            # Generate dynamic specs
            dynamic_specs = self.hypothesis_generator.generate_search_specs(video)
            video.dynamic_search_specs = dynamic_specs

        logger.info("[Orchestrator] Phase 4 complete")

    def _execute_searches(self, videos: List[Video]) -> Dict[str, List]:
        """Phase 5: Execute all search specs."""
        logger.info("[Orchestrator] Phase 5: Executing searches")

        all_results = {}

        for i, video in enumerate(videos, 1):
            logger.info(f"[Orchestrator] Searching video {i}/{len(videos)}")

            video_results = []

            # Execute static specs
            for spec in video.static_search_specs:
                result = self.search_engine.execute_search(video, spec)
                video_results.append(result)

            # Execute dynamic specs
            for spec in video.dynamic_search_specs:
                result = self.search_engine.execute_search(video, spec)
                video_results.append(result)

            all_results[video.id] = video_results

        logger.info("[Orchestrator] Phase 5 complete")
        return all_results

    def _perform_analytics(
        self,
        videos: List[Video],
        search_results: Dict[str, List]
    ) -> Dict[str, AnalyticsResult]:
        """Phase 6: Perform analytics on all videos."""
        logger.info("[Orchestrator] Phase 6: Performing analytics")

        analytics = {}

        for i, video in enumerate(videos, 1):
            logger.info(f"[Orchestrator] Analyzing video {i}/{len(videos)}")

            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze_sentiment(video.comments)

            # Topic extraction
            topics = self.topic_extractor.extract_topics(video.comments)

            # Question finding
            questions = self.question_finder.find_top_questions(video.comments)

            # Create analytics result
            result = AnalyticsResult(
                video_id=video.id,
                sentiment_score=sentiment_result.overall_score,
                sentiment_distribution=sentiment_result.distribution,
                top_topics=topics,
                top_questions=questions,
                search_results=search_results.get(video.id, []),
                metadata={'sentiment_confidence': sentiment_result.confidence}
            )

            analytics[video.id] = result

        logger.info("[Orchestrator] Phase 6 complete")
        return analytics

    def _generate_outputs(
        self,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> str:
        """Phase 7: Generate all outputs."""
        logger.info("[Orchestrator] Phase 7: Generating outputs")

        # Create run directory
        run_dir = self.output_manager.create_run_directory()

        # Save results
        self.output_manager.save_results(videos, analytics, metadata)

        logger.info(f"[Orchestrator] Phase 7 complete - Output in {run_dir}")
        return run_dir
