#!/usr/bin/env python
"""
Step 7: Generate Output Files

Usage:
    python step7_output.py intermediate/

Input:
    - intermediate/step6_analytics.pkl

Output:
    - output/run-{timestamp}/results.json
    - output/run-{timestamp}/metadata.json
    - output/run-{timestamp}/session.pkl
    - Output location printed to console
"""

import argparse
import sys
import os
import pickle
from datetime import datetime
from typing import List, Dict

from src.utils.logger import setup_logging
from src.output.output_manager import OutputManager
from src.core.session_manager import SessionManager
from src.core.models import Video, AnalyticsResult, ProcessingMetadata
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 7: Generate output files')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    parser.add_argument('--csv-file', default='dataset.csv', help='Original CSV file path (for metadata)')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 7: GENERATE OUTPUT")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load data from step 6
        input_file = os.path.join(args.data_dir, "step6_analytics.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step6_analytics.py first")
            return 1

        print(f"Loading data from: {input_file}")
        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
            analytics: Dict[str, AnalyticsResult] = data['analytics']
        print(f"✓ Loaded {len(videos)} videos")
        print(f"✓ Loaded analytics for {len(analytics)} videos")
        print()

        # Initialize output components
        output_manager = OutputManager(Config.OUTPUT_BASE_DIR)
        session_manager = SessionManager(Config.OUTPUT_BASE_DIR)

        # Create run directory
        print("Creating output directory...")
        run_dir = output_manager.create_run_directory()
        run_id = output_manager.get_run_id()
        print(f"✓ Run ID: {run_id}")
        print(f"✓ Output directory: {run_dir}")
        print()

        # Create metadata
        end_time = datetime.utcnow()
        metadata = ProcessingMetadata(
            run_id=run_id,
            start_time=end_time,  # We don't have the original start time
            input_file=args.csv_file,
            end_time=end_time,
            total_duration=0.0,  # Unknown for modular execution
            videos_processed=len(videos),
            total_comments=sum(len(v.comments) for v in videos)
        )

        # Save results
        print("Saving results...")
        output_manager.save_results(videos, analytics, metadata)
        print(f"✓ Saved results to: {os.path.join(run_dir, Config.RESULTS_FILENAME)}")
        print(f"✓ Saved metadata to: {os.path.join(run_dir, Config.METADATA_FILENAME)}")
        print()

        # Save session for reuse
        print("Saving session for reuse...")
        session_file = session_manager.save_session(run_id, videos, analytics, metadata)
        print(f"✓ Saved session to: {session_file}")
        print()

        # Summary
        print("=" * 70)
        print("STEP 7 COMPLETE")
        print("=" * 70)
        print()
        print("Output Summary:")
        print(f"  Run ID: {run_id}")
        print(f"  Directory: {run_dir}")
        print(f"  Videos: {len(videos)}")
        print(f"  Comments: {metadata.total_comments}")
        print()
        print("View results:")
        print(f"  python -m json.tool {os.path.join(run_dir, Config.RESULTS_FILENAME)}")
        print()
        print("Use this session for categorization:")
        print(f"  Session ID: {run_id}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
