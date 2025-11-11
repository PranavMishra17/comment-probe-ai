"""
Flask application for Comment Probe AI - Interactive Web UI.

Provides interactive visualization and search for analysis results.
"""

import logging
import json
import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from typing import List, Dict

from src.utils.logger import setup_logging
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

                runs.append({
                    'run_id': run_id,
                    'timestamp': metadata.get('timestamp', ''),
                    'videos': metadata.get('videos_analyzed', 0),
                    'comments': metadata.get('total_comments', 0)
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
    Searches comments across videos in a run.

    Request Body:
        {
            "run_id": "run identifier",
            "query": "search query",
            "video_ids": ["optional", "list", "of", "video", "ids"]
        }

    Returns:
        JSON with matching comments
    """
    try:
        data = request.get_json()
        run_id = data.get('run_id')
        query = data.get('query', '').lower()
        video_ids_filter = data.get('video_ids', [])

        if not run_id or not query:
            return jsonify({"error": "run_id and query are required"}), 400

        results_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", Config.RESULTS_FILENAME)

        if not os.path.exists(results_path):
            return jsonify({"error": f"Results not found for run {run_id}"}), 404

        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        # Search through videos
        matches = []
        for video in results.get('videos', []):
            video_id = video.get('video_id', '')

            # Filter by video_ids if specified
            if video_ids_filter and video_id not in video_ids_filter:
                continue

            # Search in topics
            for topic in video.get('analytics', {}).get('topics', []):
                if query in topic.get('topic_name', '').lower():
                    for comment in topic.get('representative_comments', []):
                        if query in comment.get('content', '').lower():
                            matches.append({
                                'video_id': video_id,
                                'video_url': video.get('url', ''),
                                'comment': comment.get('content', ''),
                                'match_type': 'topic',
                                'topic_name': topic.get('topic_name', ''),
                                'relevance': comment.get('relevance_score', 0)
                            })

            # Search in questions
            for question in video.get('analytics', {}).get('questions', []):
                if query in question.get('question_text', '').lower():
                    matches.append({
                        'video_id': video_id,
                        'video_url': video.get('url', ''),
                        'comment': question.get('question_text', ''),
                        'match_type': 'question',
                        'category': question.get('category', ''),
                        'relevance': question.get('relevance_score', 0)
                    })

        # Sort by relevance
        matches.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return jsonify({
            'query': query,
            'total_matches': len(matches),
            'matches': matches[:100]  # Limit to 100 results
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
