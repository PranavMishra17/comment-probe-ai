#!/usr/bin/env python
"""
Step 2: Discover Videos and Group Comments

Usage:
    python step2_discover_videos.py intermediate/

Input:
    - intermediate/step1_comments.pkl

Output:
    - intermediate/step2_videos.pkl
    - Video discovery report printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.data.video_discoverer import VideoDiscoverer
from src.core.models import Comment, Video
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 2: Discover videos and group comments')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 2: DISCOVER VIDEOS")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load comments from step 1
        input_file = os.path.join(args.data_dir, "step1_comments.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step1_load_validate.py first")
            return 1

        print(f"Loading comments from: {input_file}")
        with open(input_file, 'rb') as f:
            comments: List[Comment] = pickle.load(f)
        print(f"✓ Loaded {len(comments)} comments")
        print()

        # Initialize video discoverer
        video_discoverer = VideoDiscoverer()

        # Discover videos
        print("Discovering videos...")
        videos, orphaned = video_discoverer.discover_videos(comments)
        print(f"✓ Discovered {len(videos)} videos")
        print(f"✓ Found {len(orphaned)} orphaned comments")
        print()

        # Validate discovery
        print("Validating discovery...")
        video_discoverer.validate_discovery(videos)
        print("✓ Discovery validation passed")
        print()

        # Print video summary
        print("Video Summary:")
        print("-" * 70)
        for i, video in enumerate(videos, 1):
            print(f"{i}. Video ID: {video.id}")
            print(f"   URL: {video.url}")
            print(f"   Comments: {len(video.comments)}")
            print(f"   Title: {video.content[:60] if video.content else 'N/A'}...")
            print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step2_videos.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos, 'orphaned': orphaned}, f)

        print(f"✓ Saved to: {output_file}")
        print()
        print("=" * 70)
        print("STEP 2 COMPLETE")
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
