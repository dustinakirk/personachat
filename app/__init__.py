import logging
import logging.config
import jwt
import time
from datetime import datetime
from pathlib import Path
import os

from flask import Flask, session, g, redirect, url_for, flash

from .config import Config
from .services.gemini_service import GeminiService
from .services.supabase_service import SupabaseService
from .services.persona_service import PersonaService
from .services.conversation_service import ConversationService
from .utils import relative_time

# Configure logging
def setup_logging():
    """Configure logging for the application"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'detailed',
                'stream': 'ext://sys.stdout'
            },
        },
        'loggers': {
            'app': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console']
        }
    }

    logging.config.dictConfig(logging_config)

setup_logging()
logger = logging.getLogger(__name__)


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

    # Register custom Jinja2 filters
    app.jinja_env.filters['relative_time'] = relative_time

    @app.before_request
    def setup_authenticated_services():
        """Initialize request-scoped services with authenticated Supabase client"""
        # Always initialize services to None (prevents AttributeError)
        g.persona_service = None
        g.conversation_service = None

        if "user" in session:
            access_token = session["user"].get("access_token")
            refresh_token = session["user"].get("refresh_token")

            # Check if token needs refresh (expired or expiring within 1 hour)
            token_needs_refresh = False
            if access_token:
                try:
                    # Decode without verification to check expiry
                    decoded = jwt.decode(access_token, options={"verify_signature": False})
                    exp_timestamp = decoded.get("exp", 0)
                    current_time = time.time()
                    # Refresh if token expires within 1 hour (3600 seconds)
                    if exp_timestamp - current_time < 3600:
                        token_needs_refresh = True
                        logger.info("Access token expiring soon, will attempt refresh")
                except jwt.DecodeError:
                    logger.warning("Failed to decode access token, will attempt refresh")
                    token_needs_refresh = True
                except Exception as exc:
                    logger.warning(f"Error checking token expiry: {exc}")
                    token_needs_refresh = True

            # Attempt to refresh token if needed and refresh_token is available
            if token_needs_refresh and refresh_token:
                logger.info("Attempting to refresh access token")
                refresh_result = app.supabase_service.refresh_session(refresh_token)
                if refresh_result.success:
                    # Update session with new tokens
                    session["user"]["access_token"] = refresh_result.data.get("access_token")
                    session["user"]["refresh_token"] = refresh_result.data.get("refresh_token")
                    access_token = refresh_result.data.get("access_token")
                    logger.info("Successfully refreshed access token")
                else:
                    logger.error(f"Failed to refresh token: {refresh_result.error}")
                    # Token refresh failed - clear session and redirect to login
                    session.clear()
                    flash("Your session has expired. Please log in again.", "warning")
                    return redirect(url_for("main.login"))

            if access_token:
                # Create authenticated Supabase client for this request
                auth_client = app.supabase_service.get_authenticated_client(access_token)
                if auth_client:
                    # Initialize request-scoped services with authenticated client
                    g.persona_service = PersonaService(auth_client)
                    g.conversation_service = ConversationService(auth_client)
                else:
                    logger.error("Failed to create authenticated Supabase client for user session")
            else:
                logger.warning("User in session but no access_token found")

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
