from datetime import datetime
from pathlib import Path

from flask import Flask, session

from .config import Config
from .services.gemini_service import GeminiService
from .services.supabase_service import SupabaseService
from .services.persona_service import PersonaService
from .services.conversation_service import ConversationService


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    template_folder = base_dir / "templates"
    static_folder = base_dir / "static"

    app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
    app.config.from_object(Config)

    # Initialize Supabase service
    app.supabase_service = SupabaseService(
        url=app.config.get("SUPABASE_URL", ""),
        key=app.config.get("SUPABASE_ANON_KEY", ""),
    )

    # Initialize Gemini service
    app.gemini_service = GeminiService(
        api_key=app.config.get("GEMINI_API_KEY", ""),
        default_model=app.config.get("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash"),
        system_instruction=app.config.get("GEMINI_SYSTEM_INSTRUCTION", ""),
    )

    # Initialize Persona service (requires Supabase client)
    if app.supabase_service.is_configured:
        app.persona_service = PersonaService(app.supabase_service._client, app.supabase_service)
        app.conversation_service = ConversationService(app.supabase_service._client)
    else:
        app.persona_service = None
        app.conversation_service = None

    from .routes.main import main_bp
    from .routes.personas import personas_bp
    from .routes.conversations import conversations_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(personas_bp)
    app.register_blueprint(conversations_bp)

    @app.context_processor
    def inject_globals():
        user = session.get("user")
        return {
            "current_year": datetime.utcnow().year,
            "current_user": user,
            "user": user,
        }

    return app
