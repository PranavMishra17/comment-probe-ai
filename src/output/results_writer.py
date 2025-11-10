"""
Results JSON writer.

Generates results.json with all analysis outcomes.
"""

import logging
import json
from typing import List, Dict

from src.core.models import Video, AnalyticsResult, ProcessingMetadata

logger = logging.getLogger(__name__)


class ResultsWriter:
    """
    Generates results.json with all analysis outcomes.
    """

    def __init__(self):
        """Initialize results writer."""
        logger.info("[ResultsWriter] Initialized")

    def write_results(
        self,
        output_path: str,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> None:
        """
        Writes complete results to JSON file.

        Args:
            output_path: Path to write results.json
            videos: List of analyzed videos
            analytics: Video ID -> AnalyticsResult mapping
            metadata: Processing metadata
        """
        logger.info(f"[ResultsWriter] Writing results to {output_path}")

        # Build results structure
        results = self._build_results_structure(videos, analytics, metadata)

        # Write JSON
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"[ResultsWriter] Results written successfully")

        except Exception as e:
            logger.error(f"[ResultsWriter] Failed to write results: {e}", exc_info=True)
            raise

    def _build_results_structure(
        self,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> Dict:
        """
        Builds complete results dictionary.

        Args:
            videos: List of videos
            analytics: Analytics results
            metadata: Processing metadata

        Returns:
            Complete results dictionary
        """
        # Metadata section
        results = {
            "metadata": {
                "run_id": metadata.run_id,
                "timestamp": metadata.start_time.isoformat() if metadata.start_time else None,
                "processing_time_seconds": round(metadata.total_duration, 2),
                "input_file": metadata.input_file,
                "videos_analyzed": len(videos),
                "total_comments": sum(len(v.comments) for v in videos),
                "api_calls_made": metadata.api_calls_made,
                "api_cost_estimate": round(metadata.api_cost_estimate, 2)
            },
            "videos": []
        }

        # Videos section
        for video in videos:
            video_analytics = analytics.get(video.id)
            if not video_analytics:
                logger.warning(f"[ResultsWriter] No analytics for video {video.id}")
                continue

            video_data = {
                "video_id": video.id,
                "url": video.url,
                "title": video.content[:100],
                "author_id": video.author_id,
                "comment_count": len(video.comments),
                "analytics": video_analytics.to_dict()
            }

            results["videos"].append(video_data)

        # Summary section
        all_topics = sum(len(analytics[v.id].top_topics) for v in videos if v.id in analytics)
        all_questions = sum(len(analytics[v.id].top_questions) for v in videos if v.id in analytics)
        all_search_results = sum(len(analytics[v.id].search_results) for v in videos if v.id in analytics)
        avg_sentiment = sum(analytics[v.id].sentiment_score for v in videos if v.id in analytics) / len(videos) if videos else 0

        results["summary"] = {
            "total_topics_identified": all_topics,
            "total_questions_identified": all_questions,
            "total_search_results": all_search_results,
            "average_sentiment": round(avg_sentiment, 2)
        }

        return results
