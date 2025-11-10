#!/usr/bin/env python
"""
Migrate embeddings from pickle cache to ChromaDB.

Usage:
    python migrate_to_chromadb.py intermediate/step3_videos_embedded.pkl

This creates a ChromaDB collection from embedded comments.
"""

import argparse
import sys
import os
import pickle
from typing import List

from src.utils.logger import setup_logging
from src.utils.vector_store import VectorStore
from src.core.models import Video
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Migrate embeddings to ChromaDB')
    parser.add_argument('pickle_file', help='Path to pickle file with embedded videos')
    parser.add_argument('--collection-name', default='comments', help='ChromaDB collection name')
    parser.add_argument('--db-dir', default='./chroma_db', help='ChromaDB directory')
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", level=Config.LOG_LEVEL)

    print("=" * 70)
    print("MIGRATE TO CHROMADB")
    print("=" * 70)
    print()

    if not os.path.exists(args.pickle_file):
        print(f"Error: File not found: {args.pickle_file}")
        return 1

    try:
        # Load pickle file
        print(f"Loading embeddings from: {args.pickle_file}")
        with open(args.pickle_file, 'rb') as f:
            data = pickle.load(f)
            videos: List[Video] = data['videos']

        total_comments = sum(len(v.comments) for v in videos)
        embedded_comments = [
            c for v in videos for c in v.comments if c.embedding is not None
        ]
        print(f"✓ Loaded {len(videos)} videos")
        print(f"✓ Total comments: {total_comments}")
        print(f"✓ Embedded comments: {len(embedded_comments)}")
        print()

        # Initialize vector store
        print(f"Initializing ChromaDB in: {args.db_dir}")
        vector_store = VectorStore(persist_directory=args.db_dir)
        print("✓ ChromaDB initialized")
        print()

        # Create collection
        print(f"Creating collection: {args.collection_name}")
        vector_store.create_collection(
            name=args.collection_name,
            metadata={
                'description': 'YouTube comments embeddings',
                'source': args.pickle_file
            }
        )
        print("✓ Collection created")
        print()

        # Add comments by video
        print("Adding embeddings to ChromaDB...")
        print("-" * 70)

        total_added = 0
        for i, video in enumerate(videos, 1):
            embedded = [c for c in video.comments if c.embedding is not None]
            if not embedded:
                continue

            print(f"\nVideo {i}/{len(videos)}: {video.id}")
            print(f"  Adding {len(embedded)} embeddings...")

            vector_store.add_comments(args.collection_name, embedded)
            total_added += len(embedded)

            print(f"  ✓ Added {len(embedded)} embeddings")

        print()
        print("-" * 70)
        print(f"\n✓ Total embeddings added to ChromaDB: {total_added}")
        print()

        # Get statistics
        stats = vector_store.get_statistics(args.collection_name)
        print("Collection Statistics:")
        print(f"  Name: {stats.get('name')}")
        print(f"  Count: {stats.get('count')}")
        print(f"  Directory: {stats.get('persist_directory')}")
        print()

        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print()
        print("You can now use ChromaDB for fast similarity search!")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
