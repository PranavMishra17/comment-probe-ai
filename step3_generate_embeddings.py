#!/usr/bin/env python
"""
Step 3: Generate Embeddings for Comments

Usage:
    python step3_generate_embeddings.py intermediate/

Input:
    - intermediate/step2_videos.pkl

Output:
    - intermediate/step3_videos_embedded.pkl
    - intermediate/embeddings_cache.pkl
    - Progress and cost estimates printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.core.models import Video
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 3: Generate embeddings for comments')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 3: GENERATE EMBEDDINGS")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load videos - check for step 2.5 output first, fallback to step 2
        step2_5_file = os.path.join(args.data_dir, "step2.5_videos_reassigned.pkl")
        step2_file = os.path.join(args.data_dir, "step2_videos.pkl")

        if os.path.exists(step2_5_file):
            input_file = step2_5_file
            used_reassignment = True
            print(f"Loading videos from: {input_file} (with orphan reassignment)")
        elif os.path.exists(step2_file):
            input_file = step2_file
            used_reassignment = False
            print(f"Loading videos from: {input_file}")
            print("Note: Step 2.5 (orphan reassignment) was not run")
            print("      Run step2.5_reassign_orphaned.py to recover orphaned comments")
        else:
            print(f"Error: No input file found")
            print(f"  Tried: {step2_5_file}")
            print(f"  Tried: {step2_file}")
            print("Run step2_discover_videos.py first")
            return 1

        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
            orphaned = data.get('orphaned', [])

        print(f"Loaded {len(videos)} videos")

        total_comments = sum(len(v.comments) for v in videos)
        print(f"Total comments to embed: {total_comments}")

        if used_reassignment:
            reassignment_stats = data.get('reassignment_stats', {})
            if reassignment_stats:
                print(f"Orphan recovery stats:")
                print(f"  - Recovered: {reassignment_stats.get('recovered_by_pattern', 0) + reassignment_stats.get('recovered_by_similarity', 0)}")
                print(f"  - By pattern: {reassignment_stats.get('recovered_by_pattern', 0)}")
                print(f"  - By similarity: {reassignment_stats.get('recovered_by_similarity', 0)}")
                print(f"  - Unassigned: {reassignment_stats.get('unassigned', 0)}")
        elif orphaned:
            print(f"Found {len(orphaned)} orphaned comments (not processed)")
            print("  Consider running step2.5_reassign_orphaned.py to recover them")

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
        print("✓ Components initialized")
        print()

        # Generate embeddings
        print("Generating embeddings...")
        print("This may take several minutes depending on the number of comments.")
        print("-" * 70)

        for i, video in enumerate(videos, 1):
            print(f"\nVideo {i}/{len(videos)}: {video.id}")
            print(f"  Comments: {len(video.comments)}")

            # Embed comments
            embedder.embed_comments(video.comments)

            # Count embedded
            embedded_count = sum(1 for c in video.comments if c.embedding is not None)
            print(f"  ✓ Embedded: {embedded_count}/{len(video.comments)}")

        print()
        print("-" * 70)

        # Final statistics
        total_embedded = sum(
            sum(1 for c in v.comments if c.embedding is not None)
            for v in videos
        )
        print(f"\n✓ Total embeddings generated: {total_embedded}/{total_comments}")

        # Save cache statistics
        cache_stats = cache_manager.get_cache_stats()
        print(f"Cache hits: {cache_stats.get('cache_hits', 0)}")
        print(f"Cache misses: {cache_stats.get('cache_misses', 0)}")
        print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step3_videos_embedded.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos, 'orphaned': orphaned}, f)
        print(f"✓ Saved to: {output_file}")
        if orphaned:
            print(f"  (preserved {len(orphaned)} orphaned comments for reference)")

        # Save embeddings cache
        cache_manager.save_cache()
        cache_stats = cache_manager.get_cache_stats()
        print(f"Saved cache to: {cache_stats['cache_file']} ({cache_stats.get('cache_size_mb', 0)} MB)")
        print()

        print("=" * 70)
        print("STEP 3 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step4_generate_specs.py {args.data_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
