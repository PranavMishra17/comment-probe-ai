"""
Flask application for Comment Probe AI - Interactive Web UI.

Provides interactive visualization and search for analysis results.
"""

import logging
import json
import os
import pickle
from flask import Flask, request, jsonify, render_template, send_from_directory
from typing import List, Dict, Optional

from src.utils.logger import setup_logging
from src.core.models import CommentSearchSpec
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.search_engine import SearchEngine
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from config import Config

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Setup logging
setup_logging(log_dir="logs", level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Validate configuration
try:
    Config.validate()
    logger.info("[App] Configuration validated successfully")
except Exception as e:
    logger.error(f"[App] Configuration validation failed: {e}")
    raise

# Initialize AI components for search (lazy loading)
_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """
    Gets or initializes the search engine (singleton pattern).

    Returns:
        SearchEngine instance
    """
    global _search_engine

    if _search_engine is None:
        logger.info("[App] Initializing search engine")
        cache_manager = CacheManager(Config.CACHE_DIR)
        rate_limiter = RateLimiter(Config.REQUESTS_PER_MINUTE, Config.TOKENS_PER_MINUTE)
        openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
        embedder = Embedder(openai_client, cache_manager)
        _search_engine = SearchEngine(openai_client, embedder)
        logger.info("[App] Search engine initialized")

    return _search_engine


@app.route('/', methods=['GET'])
def index():
    """
    Serves the main interactive web UI.

    Returns:
        HTML page with run selector and visualization
    """
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.

    Returns:
        JSON with status
    """
    return jsonify({
        "status": "healthy",
        "service": "Comment Probe AI"
    })


@app.route('/api/runs', methods=['GET'])
def list_runs():
    """
    Lists all available analysis runs.

    Returns:
        JSON list of runs with metadata
    """
    try:
        if not os.path.exists(Config.OUTPUT_BASE_DIR):
            return jsonify({"runs": [], "count": 0})

        runs = []
        for item in os.listdir(Config.OUTPUT_BASE_DIR):
            if item.startswith('run-'):
                run_id = item.replace('run-', '')
                run_dir = os.path.join(Config.OUTPUT_BASE_DIR, item)

                # Load metadata if available
                metadata_path = os.path.join(run_dir, Config.METADATA_FILENAME)
                metadata = {}
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass

                # Try multiple possible field names for video count
                video_count = metadata.get('videos_processed', metadata.get('videos_analyzed', 0))
                comment_count = metadata.get('total_comments', 0)

                runs.append({
                    'run_id': run_id,
                    'timestamp': metadata.get('timestamp', ''),
                    'videos': video_count,
                    'comments': comment_count
                })

        runs.sort(key=lambda x: x['run_id'], reverse=True)  # Most recent first

        return jsonify({"runs": runs, "count": len(runs)})

    except Exception as e:
        logger.error(f"[App] Failed to list runs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/results/<run_id>', methods=['GET'])
def get_results(run_id):
    """
    Retrieves results.json for a run.

    Args:
        run_id: Run identifier

    Returns:
        JSON results
    """
    try:
        results_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", Config.RESULTS_FILENAME)

        if not os.path.exists(results_path):
            return jsonify({"error": f"Results not found for run {run_id}"}), 404

        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        return jsonify(results)

    except Exception as e:
        logger.error(f"[App] Failed to retrieve results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search_comments():
    """
    Searches comments across videos in a run using semantic search.

    Request Body:
        {
            "run_id": "run identifier",
            "query": "search query",
            "video_ids": ["optional", "list", "of", "video", "ids"],
            "top_k": 20  // optional, default 20
        }

    Returns:
        JSON with matching comments
    """
    try:
        data = request.get_json()
        run_id = data.get('run_id')
        query = data.get('query', '')
        video_ids_filter = data.get('video_ids', [])
        top_k = data.get('top_k', 20)

        if not run_id or not query:
            return jsonify({"error": "run_id and query are required"}), 400

        # Load session (which has videos with embeddings)
        session_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", "session.pkl")

        if not os.path.exists(session_path):
            return jsonify({"error": f"Session not found for run {run_id}"}), 404

        with open(session_path, 'rb') as f:
            session = pickle.load(f)

        videos = session.get('videos', [])

        if not videos:
            return jsonify({"error": "No videos found in session"}), 404

        # Initialize search engine
        search_engine = get_search_engine()

        # Create search spec
        spec = CommentSearchSpec(
            query=query,
            context="web_ui_search",
            filters={},
            extract_fields=["sentiment", "topics"],
            rationale="User-initiated web UI search",
            is_static=False,
            top_k=top_k
        )

        # Search across videos
        all_matches = []

        for video in videos:
            # Filter by video_ids if specified
            if video_ids_filter and video.id not in video_ids_filter:
                continue

            # Execute semantic search
            result = search_engine.execute_search(video, spec)

            # Convert results to JSON format
            for comment, score in zip(result.matched_comments, result.relevance_scores):
                all_matches.append({
                    'video_id': video.id,
                    'video_url': video.url,
                    'comment': comment.content,
                    'comment_url': comment.url,
                    'author_id': comment.author_id,
                    'match_type': 'semantic_search',
                    'relevance': float(score),
                    'insights': result.extracted_insights
                })

        # Sort by relevance
        all_matches.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return jsonify({
            'query': query,
            'total_matches': len(all_matches),
            'matches': all_matches[:100],  # Limit to 100 results
            'search_type': 'semantic'
        })

    except Exception as e:
        logger.error(f"[App] Search failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/video/<run_id>/<video_id>', methods=['GET'])
def get_video_details(run_id, video_id):
    """
    Gets detailed information about a specific video.

    Args:
        run_id: Run identifier
        video_id: Video identifier

    Returns:
        JSON with video details
    """
    try:
        results_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", Config.RESULTS_FILENAME)

        if not os.path.exists(results_path):
            return jsonify({"error": f"Results not found for run {run_id}"}), 404

        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        # Find the video
        for video in results.get('videos', []):
            if video.get('video_id') == video_id:
                return jsonify(video)

        return jsonify({"error": f"Video {video_id} not found"}), 404

    except Exception as e:
        logger.error(f"[App] Failed to get video details: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("[App] Starting Comment Probe AI Web UI")
    logger.info("[App] Access at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
