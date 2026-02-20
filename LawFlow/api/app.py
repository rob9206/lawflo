"""LawFlow Flask application factory."""

import logging

from flask import Flask, jsonify
from flask_cors import CORS

from api.config import config
from api.errors import APIError

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

    if not config.ANTHROPIC_API_KEY:
        logger.warning(
            "ANTHROPIC_API_KEY is not set! Document processing will fail. "
            "Add your key to the .env file."
        )
        print("\n*** WARNING: ANTHROPIC_API_KEY is not set in .env! ***")
        print("*** Document uploads will fail until you add it.   ***\n")

    # CORS for frontend dev server
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"],
         expose_headers=["X-Session-Id", "X-Tutor-Mode", "X-Topic"])

    # Error handler
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify({"error": error.message}), error.status_code

    # Health check
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "app": "LawFlow"})

    # Register blueprints
    from api.routes.documents import bp as documents_bp
    from api.routes.tutor import bp as tutor_bp
    from api.routes.progress import bp as progress_bp
    from api.routes.knowledge import bp as knowledge_bp
    from api.routes.auto_teach import bp as auto_teach_bp
    from api.routes.review import bp as review_bp
    from api.routes.exam import bp as exam_bp

    app.register_blueprint(documents_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(auto_teach_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(exam_bp)

    # Initialize database on first request
    with app.app_context():
        from api.services.database import init_database
        init_database()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
