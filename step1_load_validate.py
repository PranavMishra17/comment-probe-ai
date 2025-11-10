#!/usr/bin/env python
"""
Step 1: Load and Validate CSV Data

Usage:
    python step1_load_validate.py dataset.csv

Output:
    - intermediate/step1_comments.pkl
    - Validation report printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.data.loader import CSVLoader
from src.data.validator import DataValidator
from src.data.cleaner import DataCleaner
from src.core.models import Comment
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 1: Load and validate CSV data')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--output-dir', default='intermediate', help='Directory for intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 1: LOAD AND VALIDATE DATA")
    print("=" * 70)
    print(f"CSV File: {args.csv_file}")
    print()

    if not os.path.exists(args.csv_file):
        print(f"Error: File not found: {args.csv_file}")
        return 1

    try:
        # Validate config
        Config.validate()

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Initialize components
        csv_loader = CSVLoader(Config)
        validator = DataValidator()
        cleaner = DataCleaner()

        # Load CSV
        print("Loading CSV...")
        comments = csv_loader.load_csv(args.csv_file)
        print(f"Loaded {len(comments)} comments")
        print()

        # Validate
        print("Validating comments...")
        validation_result = validator.validate_comments(comments)

        if validation_result.is_valid:
            print("✓ All comments valid")
        else:
            print(f"⚠ Found {len(validation_result.issues_found)} validation issues:")
            for issue in validation_result.issues_found[:10]:
                print(f"  - {issue}")
            if len(validation_result.issues_found) > 10:
                print(f"  ... and {len(validation_result.issues_found) - 10} more")
        print()

        # Fix recoverable issues
        print("Fixing recoverable issues...")
        comments = validator.fix_recoverable_issues(comments)
        print(f"✓ Fixed issues, {len(comments)} comments remaining")
        print()

        # Clean comments
        print("Cleaning comments...")
        comments = cleaner.clean_comments(comments)
        print(f"✓ Cleaned {len(comments)} comments")
        print()

        # Detect spam
        print("Detecting spam...")
        original_count = len(comments)
        comments = cleaner.detect_and_remove_spam(comments)
        spam_removed = original_count - len(comments)
        print(f"✓ Removed {spam_removed} spam comments")
        print(f"✓ Final count: {len(comments)} valid comments")
        print()

        # Save intermediate state
        output_file = os.path.join(args.output_dir, "step1_comments.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump(comments, f)

        print(f"✓ Saved to: {output_file}")
        print()
        print("=" * 70)
        print("STEP 1 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step2_discover_videos.py {args.output_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
