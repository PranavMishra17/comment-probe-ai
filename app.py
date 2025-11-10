"""
Flask application for YouTube Comments Analysis System.

Provides REST API endpoints for triggering analysis and retrieving results.
"""

import logging
from flask import Flask, request, jsonify, send_file
import os

from src.utils.logger import setup_logging
from src.core.orchestrator import Orchestrator
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

# Initialize orchestrator
orchestrator = None


def get_orchestrator():
    """Gets or creates orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        orchestrator = Orchestrator(Config)
    return orchestrator


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


if __name__ == '__main__':
    logger.info("[App] Starting Flask application")
    app.run(host='0.0.0.0', port=5000, debug=False)
