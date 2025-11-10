#!/usr/bin/env python
"""
Step 4: Generate Search Specifications

Usage:
    python step4_generate_specs.py intermediate/

Input:
    - intermediate/step3_videos_embedded.pkl

Output:
    - intermediate/step4_videos_with_specs.pkl
    - Search specs printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.ai.openai_client import OpenAIClient
from src.ai.hypothesis_generator import HypothesisGenerator
from src.utils.rate_limiter import RateLimiter
from src.core.models import Video, CommentSearchSpec
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 4: Generate search specifications')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 4: GENERATE SEARCH SPECIFICATIONS")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load videos from step 3
        input_file = os.path.join(args.data_dir, "step3_videos_embedded.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step3_generate_embeddings.py first")
            return 1

        print(f"Loading videos from: {input_file}")
        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
        print(f"✓ Loaded {len(videos)} videos")
        print()

        # Initialize AI components
        print("Initializing AI components...")
        rate_limiter = RateLimiter(
            requests_per_minute=Config.REQUESTS_PER_MINUTE,
            tokens_per_minute=Config.TOKENS_PER_MINUTE
        )
        openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
        hypothesis_generator = HypothesisGenerator(openai_client)
        print("✓ Components initialized")
        print()

        # Load static specs
        print("Loading static search specs...")
        static_specs = [CommentSearchSpec.from_dict(spec) for spec in Config.STATIC_SEARCH_SPECS]
        print(f"✓ Loaded {len(static_specs)} static specs:")
        for i, spec in enumerate(static_specs, 1):
            print(f"  {i}. {spec.query[:60]}...")
        print()

        # Generate dynamic specs
        print("Generating dynamic search specs...")
        print("This will analyze each video's comments to generate custom searches.")
        print("-" * 70)

        for i, video in enumerate(videos, 1):
            print(f"\nVideo {i}/{len(videos)}: {video.id}")

            # Set static specs
            video.static_search_specs = static_specs

            # Generate dynamic specs
            print("  Generating dynamic specs...")
            dynamic_specs = hypothesis_generator.generate_search_specs(video)
            video.dynamic_search_specs = dynamic_specs

            print(f"  ✓ Generated {len(dynamic_specs)} dynamic specs:")
            for j, spec in enumerate(dynamic_specs, 1):
                print(f"    {j}. {spec.query[:60]}...")

        print()
        print("-" * 70)

        # Final statistics
        total_static = sum(len(v.static_search_specs) for v in videos)
        total_dynamic = sum(len(v.dynamic_search_specs) for v in videos)
        print(f"\n✓ Total static specs: {total_static}")
        print(f"✓ Total dynamic specs: {total_dynamic}")
        print(f"✓ Total specs: {total_static + total_dynamic}")
        print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step4_videos_with_specs.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos}, f)
        print(f"✓ Saved to: {output_file}")
        print()

        print("=" * 70)
        print("STEP 4 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step5_execute_searches.py {args.data_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
