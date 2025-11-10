#!/usr/bin/env python
"""
Step 6: Perform Analytics

Usage:
    python step6_analytics.py intermediate/

Input:
    - intermediate/step5_search_results.pkl

Output:
    - intermediate/step6_analytics.pkl
    - Analytics summary printed to console
"""

import argparse
import sys
import os
import pickle
from typing import List, Dict

from src.utils.logger import setup_logging
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.analytics.sentiment_analyzer import SentimentAnalyzer
from src.analytics.topic_extractor import TopicExtractor
from src.analytics.question_finder import QuestionFinder
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.core.models import Video, AnalyticsResult
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Step 6: Perform analytics')
    parser.add_argument('data_dir', help='Directory with intermediate files')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("STEP 6: PERFORM ANALYTICS")
    print("=" * 70)
    print()

    try:
        # Validate config
        Config.validate()

        # Load data from step 5
        input_file = os.path.join(args.data_dir, "step5_search_results.pkl")
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            print("Run step5_execute_searches.py first")
            return 1

        print(f"Loading data from: {input_file}")
        with open(input_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']
            search_results: Dict = data['search_results']
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

        sentiment_analyzer = SentimentAnalyzer(openai_client)
        topic_extractor = TopicExtractor(embedder, openai_client)
        question_finder = QuestionFinder(openai_client)
        print("✓ Components initialized")
        print()

        # Perform analytics
        print("Performing analytics...")
        print("This will analyze sentiment, extract topics, and find questions.")
        print("-" * 70)

        analytics: Dict[str, AnalyticsResult] = {}

        for i, video in enumerate(videos, 1):
            print(f"\nVideo {i}/{len(videos)}: {video.id}")
            print(f"  Analyzing {len(video.comments)} comments...")

            # Sentiment analysis
            print("  - Sentiment analysis...")
            sentiment_result = sentiment_analyzer.analyze_sentiment(video.comments)
            print(f"    ✓ Overall sentiment: {sentiment_result.overall_score:.2f}")
            print(f"    ✓ Distribution: Positive={sentiment_result.distribution.get('positive', 0)}, "
                  f"Neutral={sentiment_result.distribution.get('neutral', 0)}, "
                  f"Negative={sentiment_result.distribution.get('negative', 0)}")

            # Topic extraction
            print("  - Topic extraction...")
            topics = topic_extractor.extract_topics(video.comments)
            print(f"    ✓ Extracted {len(topics)} topics:")
            for j, topic in enumerate(topics, 1):
                print(f"      {j}. {topic.topic_name} ({len(topic.comment_ids)} comments)")

            # Question finding
            print("  - Question finding...")
            questions = question_finder.find_top_questions(video.comments)
            print(f"    ✓ Found {len(questions)} top questions")

            # Create analytics result
            result = AnalyticsResult(
                video_id=video.id,
                sentiment_score=sentiment_result.overall_score,
                sentiment_distribution=sentiment_result.distribution,
                top_topics=topics,
                top_questions=questions,
                search_results=search_results.get(video.id, []),
                metadata={'sentiment_confidence': sentiment_result.confidence}
            )

            analytics[video.id] = result

        print()
        print("-" * 70)

        # Final statistics
        total_topics = sum(len(a.top_topics) for a in analytics.values())
        total_questions = sum(len(a.top_questions) for a in analytics.values())
        avg_sentiment = sum(a.sentiment_score for a in analytics.values()) / len(analytics)

        print(f"\n✓ Total topics extracted: {total_topics}")
        print(f"✓ Total questions found: {total_questions}")
        print(f"✓ Average sentiment score: {avg_sentiment:.2f}")
        print()

        # Save intermediate state
        output_file = os.path.join(args.data_dir, "step6_analytics.pkl")
        with open(output_file, 'wb') as f:
            pickle.dump({'videos': videos, 'analytics': analytics}, f)
        print(f"✓ Saved to: {output_file}")
        print()

        print("=" * 70)
        print("STEP 6 COMPLETE")
        print("=" * 70)
        print()
        print("Next step:")
        print(f"  python step7_output.py {args.data_dir}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
