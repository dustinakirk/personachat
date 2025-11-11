from datetime import datetime
from pathlib import Path

from flask import Flask, session

from .config import Config
from .services.gemini_service import GeminiService
from .services.supabase_service import SupabaseService


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    template_folder = base_dir / "templates"
    static_folder = base_dir / "static"

    app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
    app.config.from_object(Config)

    app.supabase_service = SupabaseService(
        url=app.config.get("SUPABASE_URL", ""),
        key=app.config.get("SUPABASE_ANON_KEY", ""),
    )
    app.gemini_service = GeminiService(api_key=app.config.get("GEMINI_API_KEY", ""))

    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_globals():
        user = session.get("user")
        return {
            "current_year": datetime.utcnow().year,
            "current_user": user,
            "user": user,
        }

    return app
