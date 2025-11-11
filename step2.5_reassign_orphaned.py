#!/usr/bin/env python
"""
Step 2.5: Reassign Orphaned Comments (Optional)

This optional step attempts to recover orphaned comments by reassigning them
to videos using intelligent pattern matching and semantic similarity.

Usage:
    python step2.5_reassign_orphaned.py intermediate/

Input:
    - intermediate/step2_videos.pkl

Output:
    - intermediate/step2.5_videos_reassigned.pkl
    - Reassignment statistics printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.data.orphaned_reassigner import OrphanedCommentReassigner
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.core.models import Video, Comment
from config import Config

def main():
    parser = argparse.ArgumentParser(
        description='Step 2.5: Reassign orphaned comments (optional)'
    )
    parser.add_argument('data_dir', help='Directory with intermediate files')
    parser.add_argument(
        '--skip-similarity',
        action='store_true',
        help='Skip semantic similarity matching (faster, pattern-only)'
    )
    parser.add_argument(
        '--no-prompt',
        action='store_true',
        help='Skip interactive warning prompt (for automated workflows)'
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 2.5: REASSIGN ORPHANED COMMENTS (OPTIONAL)")
    print("=" * 70)
    print()
    print("WARNING: Orphaned comments may not belong to your videos!")
    print("They could be replies to other comments or from different videos.")
    print("Reassignment based on semantic similarity may introduce noise.")
    print("Consider reviewing USAGE.md for important caveats before proceeding.")
    print()
    print("Recommended settings to avoid contamination:")
    print("  - SEMANTIC_SIMILARITY_THRESHOLD=0.85 (high confidence)")
    print("  - SKIP_REASSIGNED_IN_ANALYTICS=true (exclude from analysis)")
    print()

    if not args.no_prompt:
        input("Press Enter to continue or Ctrl+C to cancel...")
        print()

    try:
        # Validate config
        Config.validate()

        # Load videos from step 2
        input_file = os.path.join(args.data_dir, "step2_videos.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step2_discover_videos.py first")
            return 1

        print(f"Loading videos from: {input_file}")
        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
            orphaned: List[Comment] = data.get('orphaned', [])

        print(f"Loaded {len(videos)} videos")
        print(f"Found {len(orphaned)} orphaned comments")
        print()

        if not orphaned:
            print("No orphaned comments to reassign!")
            print("Skipping step 2.5...")
            print()
            print("You can proceed directly to step 3:")
            print(f"  python step3_generate_embeddings.py {args.data_dir}")
            return 0

        # Initialize embedder if semantic matching is enabled
        embedder = None
        if not args.skip_similarity and Config.ENABLE_ORPHAN_REASSIGNMENT:
            print("Initializing AI components for semantic matching...")
            cache_manager = CacheManager(Config.CACHE_DIR)
            rate_limiter = RateLimiter(
                requests_per_minute=Config.REQUESTS_PER_MINUTE,
                tokens_per_minute=Config.TOKENS_PER_MINUTE
            )
            openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
            embedder = Embedder(openai_client, cache_manager)
            print("Components initialized")
            print()
        elif args.skip_similarity:
            print("Semantic matching disabled (--skip-similarity)")
            print("Will use pattern matching only")
            print()

        # Embed video comments first (required for semantic matching)
        if embedder:
            print("Embedding video comments for similarity matching...")
            print("This is required for semantic reassignment to work.")
            print()

            for i, video in enumerate(videos, 1):
                print(f"Embedding video {i}/{len(videos)}: {video.id}")
                print(f"  Comments: {len(video.comments)}")
                embedder.embed_comments(video.comments)
                embedded_count = sum(1 for c in video.comments if c.embedding is not None)
                print(f"  Embedded: {embedded_count}/{len(video.comments)}")

            print()
            print("Video embeddings complete")
            print()

        # Initialize reassigner
        print("Initializing orphaned comment reassigner...")
        reassigner = OrphanedCommentReassigner(
            embedder=embedder,
            similarity_threshold=Config.SEMANTIC_SIMILARITY_THRESHOLD,
            create_unassigned_video=Config.CREATE_UNASSIGNED_VIDEO
        )
        print()

        # Run reassignment
        print("Starting reassignment process...")
        print("=" * 70)
        print()
        print("This may take several minutes for large datasets...")
        print(f"Processing {len(orphaned)} orphaned comments against {len(videos)} videos")
        print()

        videos_updated, stats = reassigner.reassign_comments(videos, orphaned)

        print()
        print("=" * 70)
        print()

        # Print summary
        print("Reassignment Summary:")
        print("-" * 70)
        print(f"Total orphaned comments: {stats['total_orphaned']}")
        print(f"Recovered by pattern matching: {stats['recovered_by_pattern']}")
        print(f"Recovered by semantic similarity: {stats['recovered_by_similarity']}")
        print(f"Remaining unassigned: {stats['unassigned']}")
        print(f"Recovery rate: {stats['recovery_rate']:.1%}")
        print()

        # Video summary
        print("Updated Video Summary:")
        print("-" * 70)
        for i, video in enumerate(videos_updated, 1):
            reassigned_count = sum(
                1 for c in video.comments
                if c.metadata.get('reassigned')
            )
            original_count = len(video.comments) - reassigned_count

            print(f"{i}. Video ID: {video.id}")
            print(f"   Total comments: {len(video.comments)}")
            print(f"   Original: {original_count}")
            print(f"   Reassigned: {reassigned_count}")

            if video.video_metadata.get('is_unassigned'):
                print(f"   [VIRTUAL: Unassigned Comments Group]")

            print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step2.5_videos_reassigned.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({
                'videos': videos_updated,
                'orphaned': [],  # All orphaned have been processed
                'reassignment_stats': stats
            }, f)

        print(f"Saved to: {output_file}")
        print()

        print("=" * 70)
        print("STEP 2.5 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step3_generate_embeddings.py {args.data_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
