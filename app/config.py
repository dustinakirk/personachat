import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a local .env when running outside of Vercel
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:8000")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
