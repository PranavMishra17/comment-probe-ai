"""
Flask application for YouTube Comments Analysis System.

Provides REST API endpoints for triggering analysis and retrieving results.
"""

import logging
from flask import Flask, request, jsonify, send_file, render_template
import os

from src.utils.logger import setup_logging
from src.core.orchestrator import Orchestrator
from src.core.session_manager import SessionManager
from src.core.models import Comment
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.utils.helpers import compute_cosine_similarity
from config import Config

# Initialize Flask app
app = Flask(__name__)

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

# Initialize components
orchestrator = None
session_manager = SessionManager(Config.OUTPUT_BASE_DIR)


def get_orchestrator():
    """Gets or creates orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        orchestrator = Orchestrator(Config)
    return orchestrator


@app.route('/', methods=['GET'])
def index():
    """
    Serves the main web UI.

    Returns:
        HTML page
    """
    return render_template('index.html')
  
  
def root():
    """
    Root endpoint providing API documentation.

    Returns:
        JSON with available endpoints
    """
    return jsonify({
        "service": "YouTube Comments Analysis System",
        "version": "1.0",
        "endpoints": {
            "GET /": "API documentation (this endpoint)",
            "GET /health": "Health check",
            "POST /analyze": "Start analysis of a CSV file",
            "GET /results/<run_id>": "Retrieve results for a run",
            "GET /runs": "List all available runs"
        },
        "example_request": {
            "method": "POST",
            "path": "/analyze",
            "body": {"csv_path": "/path/to/comments.csv"}
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.

    Returns:
        JSON with status
    """
    return jsonify({
        "status": "healthy",
        "service": "YouTube Comments Analysis System"
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Triggers analysis of CSV file.

    Request Body:
        {
            "csv_path": "path/to/file.csv"
        }

    Returns:
        JSON with run_id and status
    """
    try:
        data = request.get_json()
        csv_path = data.get('csv_path')

        if not csv_path:
            return jsonify({"error": "csv_path is required"}), 400

        if not os.path.exists(csv_path):
            return jsonify({"error": f"File not found: {csv_path}"}), 404

        logger.info(f"[App] Starting analysis of {csv_path}")

        # Run analysis
        orch = get_orchestrator()
        run_id = orch.run_analysis(csv_path)

        # Save session for reuse
        try:
            session_data = session_manager.load_session(run_id)
            logger.info(f"[App] Session data available for reuse")
        except Exception as e:
            logger.warning(f"[App] Could not save session: {e}")

        logger.info(f"[App] Analysis complete - Run ID: {run_id}")

        return jsonify({
            "status": "complete",
            "run_id": run_id,
            "message": f"Analysis complete. Results available in output/run-{run_id}/"
        })

    except Exception as e:
        logger.error(f"[App] Analysis failed: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/results/<run_id>', methods=['GET'])
def get_results(run_id):
    """
    Retrieves results.json for a run.

    Args:
        run_id: Run identifier

    Returns:
        JSON results file
    """
    try:
        results_path = os.path.join(Config.OUTPUT_BASE_DIR, f"run-{run_id}", Config.RESULTS_FILENAME)

        if not os.path.exists(results_path):
            return jsonify({"error": f"Results not found for run {run_id}"}), 404

        return send_file(results_path, mimetype='application/json')

    except Exception as e:
        logger.error(f"[App] Failed to retrieve results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/runs', methods=['GET'])
def list_runs():
    """
    Lists all available runs.

    Returns:
        JSON list of run IDs
    """
    try:
        if not os.path.exists(Config.OUTPUT_BASE_DIR):
            return jsonify({"runs": []})

        runs = []
        for item in os.listdir(Config.OUTPUT_BASE_DIR):
            if item.startswith('run-'):
                run_id = item.replace('run-', '')
                runs.append(run_id)

        runs.sort(reverse=True)  # Most recent first

        return jsonify({"runs": runs, "count": len(runs)})

    except Exception as e:
        logger.error(f"[App] Failed to list runs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/categorize', methods=['POST'])
def categorize_comment():
    """
    Categorizes a new comment using an existing session.

    Request Body:
        {
            "session_id": "run_id",
            "comment": "comment text"
        }

    Returns:
        JSON with categorization results
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        comment_text = data.get('comment')

        if not session_id or not comment_text:
            return jsonify({"error": "session_id and comment are required"}), 400

        logger.info(f"[App] Categorizing comment using session {session_id}")

        # Load session
        session = session_manager.load_session(session_id)
        if not session:
            return jsonify({"error": f"Session {session_id} not found"}), 404

        # Initialize AI components for categorization
        cache_mgr = CacheManager(Config.CACHE_DIR)
        rate_limiter = RateLimiter(Config.REQUESTS_PER_MINUTE, Config.TOKENS_PER_MINUTE)
        openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
        embedder = Embedder(openai_client, cache_mgr)

        # Create comment object
        new_comment = Comment(
            id="new_comment",
            url="",
            content=comment_text,
            author_id="unknown",
            parent_id="unknown"
        )
        new_comment.cleaned_content = comment_text

        # Generate embedding
        new_comment.embedding = embedder.embed_text(comment_text)

        # Find most similar topic
        videos = session.get('videos', [])
        best_similarity = 0
        best_topic = "Unknown"
        best_video = None

        for video in videos:
            for comment in video.comments[:50]:  # Sample for performance
                if comment.embedding:
                    similarity = compute_cosine_similarity(
                        new_comment.embedding,
                        comment.embedding
                    )
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_video = video

        # Get analytics for best matching video
        analytics = session.get('analytics', {})
        if best_video and best_video.id in analytics:
            video_analytics = analytics[best_video.id]
            if video_analytics.top_topics:
                best_topic = video_analytics.top_topics[0].topic_name

        # Simple sentiment estimation (0-1)
        sentiment_words_positive = ['good', 'great', 'love', 'excellent', 'awesome', 'thanks']
        sentiment_words_negative = ['bad', 'hate', 'terrible', 'awful', 'worst', 'disappointed']

        text_lower = comment_text.lower()
        sentiment = 0.5  # Neutral default

        positive_count = sum(1 for word in sentiment_words_positive if word in text_lower)
        negative_count = sum(1 for word in sentiment_words_negative if word in text_lower)

        if positive_count > negative_count:
            sentiment = 0.7 + (positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = 0.3 - (negative_count * 0.1)

        sentiment = max(0, min(1, sentiment))  # Clamp to 0-1

        # Determine category
        if '?' in comment_text:
            category = "question"
        elif any(word in text_lower for word in ['suggest', 'should', 'could', 'would']):
            category = "suggestion"
        elif any(word in text_lower for word in ['issue', 'problem', 'bug', 'error']):
            category = "issue"
        else:
            category = "feedback"

        logger.info(f"[App] Categorization complete")

        return jsonify({
            "sentiment": sentiment,
            "similar_topic": best_topic,
            "similarity_score": best_similarity,
            "category": category,
            "comment": comment_text
        })

    except Exception as e:
        logger.error(f"[App] Categorization failed: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    logger.info("[App] Starting Flask application")
    logger.info("[App] Web UI available at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
