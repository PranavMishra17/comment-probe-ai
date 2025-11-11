"""
Standalone CLI tool for testing semantic search on analysis results.

Usage:
    python search_cli.py <run_id> "<search_query>" [--video-id VIDEO_ID] [--top-k N]

Examples:
    python search_cli.py 20251110_070350 "technical questions about performance"
    python search_cli.py 20251110_070350 "feature requests" --video-id FqIMu4C87SM --top-k 10
"""

import argparse
import logging
import pickle
import os
import sys
from typing import Optional

from src.core.models import Video, CommentSearchSpec
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.search_engine import SearchEngine
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.utils.logger import setup_logging
from config import Config

logger = logging.getLogger(__name__)


def load_session(run_id: str) -> dict:
    """
    Loads a previous analysis session.

    Args:
        run_id: Run identifier

    Returns:
        Session data with videos and analytics
    """
    session_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", "session.pkl")

    if not os.path.exists(session_path):
        raise FileNotFoundError(f"Session not found: {session_path}")

    logger.info(f"[SearchCLI] Loading session from {session_path}")

    with open(session_path, 'rb') as f:
        session = pickle.load(f)

    logger.info(f"[SearchCLI] Loaded session with {len(session.get('videos', []))} videos")

    return session


def find_video(videos: list, video_id: Optional[str] = None) -> Video:
    """
    Finds a video by ID or returns first video.

    Args:
        videos: List of videos
        video_id: Optional video ID to find

    Returns:
        Video object
    """
    if video_id:
        for video in videos:
            if video.id == video_id:
                return video
        raise ValueError(f"Video not found: {video_id}")

    return videos[0]


def perform_search(
    video: Video,
    query: str,
    top_k: int,
    search_engine: SearchEngine
):
    """
    Performs search on video comments.

    Args:
        video: Video to search
        query: Search query
        top_k: Number of results
        search_engine: Search engine instance
    """
    logger.info(f"[SearchCLI] Performing search on video {video.id}")
    logger.info(f"[SearchCLI] Query: {query}")
    logger.info(f"[SearchCLI] Top K: {top_k}")

    # Create search spec
    spec = CommentSearchSpec(
        query=query,
        context="cli_search",
        filters={},
        extract_fields=["sentiment", "topics"],
        rationale="User-initiated CLI search",
        is_static=False,
        top_k=top_k
    )

    # Execute search
    result = search_engine.execute_search(video, spec)

    # Display results
    print("\n" + "=" * 80)
    print(f"SEARCH RESULTS FOR: {query}")
    print("=" * 80)
    print(f"Video: {video.url}")
    print(f"Total comments searched: {len(video.comments)}")
    print(f"Results found: {len(result.matched_comments)}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print(f"API calls made: {result.api_calls_made}")
    print("=" * 80)

    if len(result.matched_comments) == 0:
        print("\nNo results found.")
        return

    # Display each result
    for i, (comment, score) in enumerate(zip(result.matched_comments, result.relevance_scores)):
        print(f"\n[RESULT {i+1}] Relevance: {score:.3f}")
        print(f"Author: {comment.author_id}")
        print(f"URL: {comment.url}")
        print(f"Content: {comment.content[:200]}{'...' if len(comment.content) > 200 else ''}")
        print("-" * 80)

    # Display insights
    if result.extracted_insights:
        print("\nEXTRACTED INSIGHTS:")
        for key, value in result.extracted_insights.items():
            print(f"  {key}: {value}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Search comments in YouTube analysis results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search_cli.py 20251110_070350 "technical questions"
  python search_cli.py 20251110_070350 "feature requests" --video-id FqIMu4C87SM
  python search_cli.py 20251110_070350 "bugs and issues" --top-k 20
        """
    )

    parser.add_argument('run_id', help='Run identifier (e.g., 20251110_070350)')
    parser.add_argument('query', help='Search query in quotes')
    parser.add_argument('--video-id', help='Specific video ID to search (optional)')
    parser.add_argument('--top-k', type=int, default=10, help='Number of results to return (default: 10)')
    parser.add_argument('--log-level', default='INFO', help='Logging level (default: INFO)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=args.log_level)

    try:
        # Validate config
        Config.validate()

        # Load session
        print(f"Loading session: {args.run_id}...")
        session = load_session(args.run_id)

        videos = session.get('videos', [])
        if not videos:
            print("ERROR: No videos found in session")
            sys.exit(1)

        # Find target video
        video = find_video(videos, args.video_id)
        print(f"Searching video: {video.id} ({len(video.comments)} comments)")

        # Initialize AI components
        print("Initializing search engine...")
        cache_manager = CacheManager(Config.CACHE_DIR)
        rate_limiter = RateLimiter(Config.REQUESTS_PER_MINUTE, Config.TOKENS_PER_MINUTE)
        openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
        embedder = Embedder(openai_client, cache_manager)
        search_engine = SearchEngine(openai_client, embedder)

        # Perform search
        perform_search(video, args.query, args.top_k, search_engine)

        print("\nSearch complete!")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print(f"\nAvailable runs:")
        if os.path.exists(Config.OUTPUT_BASE_DIR):
            runs = [d.replace('run-', '') for d in os.listdir(Config.OUTPUT_BASE_DIR) if d.startswith('run-')]
            for run in sorted(runs, reverse=True):
                print(f"  - {run}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"[SearchCLI] Search failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
