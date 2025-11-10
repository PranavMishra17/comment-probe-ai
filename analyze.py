#!/usr/bin/env python
"""
Command-line script for analyzing YouTube comments.

Usage:
    python analyze.py dataset.csv
    python analyze.py --csv dataset.csv
    python analyze.py --csv dataset.csv --load-session 20241110_143215
"""

import argparse
import sys
import os

from src.utils.logger import setup_logging
from src.core.orchestrator import Orchestrator
from config import Config

def main():
    """Main entry point for CLI analysis."""
    parser = argparse.ArgumentParser(
        description='Analyze YouTube comments with AI-powered insights'
    )
    parser.add_argument(
        'csv_file',
        nargs='?',
        help='Path to CSV file with comments'
    )
    parser.add_argument(
        '--csv',
        dest='csv_path',
        help='Path to CSV file (alternative syntax)'
    )
    parser.add_argument(
        '--load-session',
        dest='session_id',
        help='Load and reuse embeddings from a previous session'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    # Determine CSV path
    csv_path = args.csv_file or args.csv_path
    if not csv_path:
        parser.error('CSV file path is required')

    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    # Setup logging
    setup_logging(log_dir="logs", level=args.log_level)

    print("=" * 60)
    print("YouTube Comments Analysis System")
    print("=" * 60)
    print(f"CSV File: {csv_path}")
    if args.session_id:
        print(f"Loading session: {args.session_id}")
    print()

    try:
        # Validate configuration
        Config.validate()
        print("Configuration validated")

        # Initialize orchestrator
        print("Initializing system...")
        orchestrator = Orchestrator(Config)

        # Run analysis
        print("\nStarting analysis...")
        print("This may take several minutes depending on the number of comments.")
        print("-" * 60)

        run_id = orchestrator.run_analysis(csv_path)

        print("-" * 60)
        print("\nAnalysis complete!")
        print(f"Run ID: {run_id}")
        print(f"Results: output/run-{run_id}/results.json")
        print(f"Logs: output/run-{run_id}/logs/")
        print()
        print("To view results:")
        print(f"  python -m json.tool output/run-{run_id}/results.json")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        print("\nCheck logs/errors.log for details")
        return 1


if __name__ == '__main__':
    sys.exit(main())
