"""LawFlow Flask application factory."""

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from api.config import config
from api.errors import APIError

logger = logging.getLogger(__name__)


def create_app(static_dir: str | None = None) -> Flask:
    resolved_static_dir: str | None = None
    if static_dir:
        candidate = Path(static_dir).resolve()
        if candidate.exists():
            resolved_static_dir = str(candidate)

    app = Flask(
        __name__,
        static_folder=resolved_static_dir,
        static_url_path="" if resolved_static_dir else None,
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

    if not config.ANTHROPIC_API_KEY:
        logger.warning(
            "ANTHROPIC_API_KEY is not set! Document processing will fail. "
            "Add your key to the .env file."
        )
        print("\n*** WARNING: ANTHROPIC_API_KEY is not set in .env! ***")
        print("*** Document uploads will fail until you add it.   ***\n")

    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    extra_origins = os.getenv("ALLOWED_ORIGINS", "")
    if extra_origins:
        allowed_origins.extend(o.strip() for o in extra_origins.split(",") if o.strip())

    CORS(app, origins=allowed_origins,
         expose_headers=["X-Session-Id", "X-Tutor-Mode", "X-Topic"])

    # Error handler
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify({"error": error.message}), error.status_code

    # Health check
    @app.route("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "app": "LawFlow",
                "debug_app_marker": "DBG_APP_5002",
                "app_file": __file__,
            }
        )

    # Seed database on demand (subjects/topics); safe to call multiple times
    @app.route("/api/seed", methods=["POST"])
    def seed():
        from api.services.subject_taxonomy import seed_subject_taxonomy
        seed_subject_taxonomy()
        return jsonify({"status": "ok", "message": "Subject and topic taxonomy seeded."})

    # Register blueprints
    from api.routes.documents import bp as documents_bp
    from api.routes.tutor import bp as tutor_bp
    from api.routes.progress import bp as progress_bp
    from api.routes.knowledge import bp as knowledge_bp
    from api.routes.auto_teach import bp as auto_teach_bp
    from api.routes.review import bp as review_bp
    from api.routes.exam import bp as exam_bp
    from api.routes.profile import bp as profile_bp
    from api.routes.rewards import bp as rewards_bp

    app.register_blueprint(documents_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(auto_teach_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(rewards_bp)

    if resolved_static_dir:
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path: str):
            if path.startswith("api/"):
                return jsonify({"error": "Not found"}), 404

            file_path = Path(resolved_static_dir) / path
            if path and file_path.is_file():
                return send_from_directory(resolved_static_dir, path)
            return send_from_directory(resolved_static_dir, "index.html")

    # Initialize database and seed achievements
    with app.app_context():
        from api.services.database import init_database
        init_database()

        from api.services.achievement_definitions import seed_achievements
        seed_achievements()

        from api.services.subject_taxonomy import seed_subject_taxonomy
        seed_subject_taxonomy()

    return app


# Auto-detect built frontend so gunicorn serves the SPA in production.
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
app = create_app(static_dir=str(_dist) if _dist.is_dir() else None)

if __name__ == "__main__":
    # Reloader disabled: module-level create_app() imports blueprints and
    # touches DB/cache files on every reimport, which the stat reloader
    # detects as changes → infinite restart loop.
    # For auto-reloading in dev, use the launch.json "api" config instead
    # (flask CLI handles factory-pattern reloading correctly).
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG,
            use_reloader=False)
