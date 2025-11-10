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
        print(f"✓ Loaded {len(videos)} videos")

        total_comments = sum(len(v.comments) for v in videos)
        print(f"✓ Total comments to embed: {total_comments}")
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
        cache_stats = cache_manager.get_statistics()
        print(f"✓ Cache hits: {cache_stats.get('hits', 0)}")
        print(f"✓ Cache misses: {cache_stats.get('misses', 0)}")
        print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step3_videos_embedded.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos}, f)
        print(f"✓ Saved to: {output_file}")

        # Save embeddings cache
        cache_file = os.path.join(args.data_dir, "embeddings_cache.pkl")
        cache_manager.save_cache(cache_file)
        print(f"✓ Saved cache to: {cache_file}")
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
