from datetime import datetime
from pathlib import Path

from flask import Flask, session, g, redirect, url_for, flash

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

    # Request-scoped services are initialized in before_request handler
    # (PersonaService and ConversationService are created per-request with authenticated client)

    from .routes.main import main_bp
    from .routes.personas import personas_bp
    from .routes.conversations import conversations_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(personas_bp)
    app.register_blueprint(conversations_bp)

    @app.before_request
    def setup_authenticated_services():
        """Initialize request-scoped services with authenticated Supabase client"""
        if "user" in session:
            access_token = session["user"].get("access_token")
            if access_token:
                # Create authenticated Supabase client for this request
                auth_client = app.supabase_service.get_authenticated_client(access_token)
                if auth_client:
                    # Initialize request-scoped services with authenticated client
                    g.persona_service = PersonaService(auth_client)
                    g.conversation_service = ConversationService(auth_client)

    @app.errorhandler(Exception)
    def handle_jwt_expired(error):
        """Handle JWT expiration and other authentication errors"""
        # Check if it's a JWT expired error
        error_str = str(error)
        if "JWT expired" in error_str or "PGRST303" in error_str:
            # Clear the session
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("main.login"))
        # Re-raise other exceptions
        raise error

    @app.context_processor
    def inject_globals():
        user = session.get("user")
        return {
            "current_year": datetime.utcnow().year,
            "current_user": user,
            "user": user,
        }

    return app
