"""
Flask server — entry point for the Lecture AI system.
Localhost only, token-based auth.
"""

import logging
import sys
from functools import wraps

from flask import Flask, request, jsonify

from . import config, database
from .session_manager import SessionManager

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(config.DATA_DIR / "lecture_ai.log")),
    ],
)
logger = logging.getLogger(__name__)

# ---- App ----
app = Flask(__name__)
session_mgr = SessionManager()


# ---- Auth middleware ----
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth[7:]  # strip "Bearer "
        if token != config.AUTH_TOKEN:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# ---- Routes ----

@app.route("/start", methods=["POST"])
@require_auth
def start_session():
    """Start a new capture session."""
    result = session_mgr.start_session()
    if "error" in result:
        return jsonify(result), 409
    return jsonify(result), 200


@app.route("/stop", methods=["POST"])
@require_auth
def stop_session():
    """Stop the current session."""
    result = session_mgr.stop_session()
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 200


@app.route("/status", methods=["GET"])
@require_auth
def get_status():
    """Get current session status."""
    return jsonify(session_mgr.get_status()), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check — no auth required."""
    return jsonify({"status": "ok"}), 200


# ---- Entry point ----
def main():
    """Initialize DB and start the Flask server."""
    logger.info("Initializing Lecture AI system...")
    database.init_db()
    logger.info(f"Database ready at {config.DB_PATH}")
    logger.info(f"Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")

    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
