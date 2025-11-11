#!/usr/bin/env python
"""
Step 5: Execute Search Specifications

Usage:
    python step5_execute_searches.py intermediate/

Input:
    - intermediate/step4_videos_with_specs.pkl

Output:
    - intermediate/step5_search_results.pkl
    - Search results summary printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List, Dict

from src.utils.logger import setup_logging
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.search_engine import SearchEngine
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.core.models import Video
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 5: Execute search specifications')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 5: EXECUTE SEARCHES")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load videos from step 4
        input_file = os.path.join(args.data_dir, "step4_videos_with_specs.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step4_generate_specs.py first")
            return 1

        print(f"Loading videos from: {input_file}")
        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
            orphaned = data.get('orphaned', [])
        print(f"✓ Loaded {len(videos)} videos")
        print()

        # Initialize AI components
        print("Initializing AI components...")
        cache_manager = CacheManager(Config.CACHE_DIR)
        rate_limiter = RateLimiter(
            requests_per_minute=Config.REQUESTS_PER_MINUTE,
            tokens_per_minute=Config.TOKENS_PER_MINUTE
        )
        openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
        embedder = Embedder(openai_client, cache_manager)
        search_engine = SearchEngine(openai_client, embedder)
        print("✓ Components initialized")
        print()

        # Execute searches
        print("Executing searches...")
        print("This will perform semantic search + LLM ranking for each spec.")
        print("-" * 70)

        all_results: Dict[str, List] = {}

        for i, video in enumerate(videos, 1):
            # Skip UNASSIGNED virtual video if configured
            if Config.SKIP_UNASSIGNED_IN_ANALYTICS and video.video_metadata.get('is_unassigned'):
                print(f"\nVideo {i}/{len(videos)}: {video.id} [SKIPPED - Unassigned Group]")
                continue

            print(f"\nVideo {i}/{len(videos)}: {video.id}")

            # Report on reassigned comments if present
            reassigned_count = sum(1 for c in video.comments if c.metadata.get('reassigned'))
            if reassigned_count > 0:
                print(f"  Note: {reassigned_count}/{len(video.comments)} comments are reassigned (may affect search relevance)")

            total_specs = len(video.static_search_specs) + len(video.dynamic_search_specs)
            print(f"  Total search specs: {total_specs}")

            video_results = []

            # Execute static specs
            print(f"  Executing {len(video.static_search_specs)} static specs...")
            for j, spec in enumerate(video.static_search_specs, 1):
                result = search_engine.execute_search(video, spec)
                video_results.append(result)
                print(f"    {j}. {spec.query[:50]}... → {len(result.matched_comments)} results")

            # Execute dynamic specs
            print(f"  Executing {len(video.dynamic_search_specs)} dynamic specs...")
            for j, spec in enumerate(video.dynamic_search_specs, 1):
                result = search_engine.execute_search(video, spec)
                video_results.append(result)
                print(f"    {j}. {spec.query[:50]}... → {len(result.matched_comments)} results")

            all_results[video.id] = video_results
            print(f"  ✓ Completed {len(video_results)} searches")

        print()
        print("-" * 70)

        # Final statistics
        total_searches = sum(len(results) for results in all_results.values())
        total_comments_found = sum(
            len(result.matched_comments)
            for results in all_results.values()
            for result in results
        )
        print(f"\n✓ Total searches executed: {total_searches}")
        print(f"✓ Total comments found: {total_comments_found}")
        print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step5_search_results.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos, 'search_results': all_results, 'orphaned': orphaned}, f)
        print(f"✓ Saved to: {output_file}")
        print()

        print("=" * 70)
        print("STEP 5 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step6_analytics.py {args.data_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
