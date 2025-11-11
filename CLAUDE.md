# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PersonaChat is a Flask web application designed for Vercel serverless deployment. It integrates Supabase for authentication/storage and Google Gemini for AI-powered responses. The app uses server-side rendering with Jinja2 templates and session-based authentication.

## Development Commands

### Local Development
```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
python api/index.py
# Server runs on http://127.0.0.1:8000
```

### Testing & Deployment
```bash
# Deploy to Vercel
vercel                    # Initial setup
vercel deploy --prod      # Production deployment

# Set environment variables on Vercel
vercel env add FLASK_SECRET_KEY
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add GEMINI_API_KEY
vercel env add SESSION_COOKIE_SECURE
```

## Architecture

### Application Factory Pattern
The app uses Flask's application factory pattern with a single entry point:
- `api/index.py` - Vercel serverless entry point, imports `create_app()` from `app/__init__.py`
- `app/__init__.py` - Defines `create_app()` factory that:
  - Configures Flask app with templates/static paths
  - Initializes service wrappers (Supabase, Gemini) as app attributes
  - Registers blueprints (currently only `main_bp`)
  - Injects global context variables (`current_user`, `current_year`)

### Service Layer Pattern
Services are initialized once during app creation and attached to the Flask app object:
- `app.supabase_service` (SupabaseService) - Authentication and database wrapper with methods:
  - Authentication: `register_user()`, `login_user()`
  - Database: `save_conversation()`, `get_user_conversations()`, `create_user_profile()`, `get_user_profile()`, `update_user_profile()`
  - All methods return `SupabaseResult` dataclass with `success`, `data`, `error` fields
- `app.gemini_service` (GeminiService) - AI generation wrapper with `generate_response()` method using `gemini-pro` model

Both services implement an `is_configured` property to gracefully handle missing API keys.

### Route Organization
Routes are organized in blueprints within `app/routes/`:
- `main.py` - Contains all public routes (`/`, `/application`, `/register`, `/login`, `/logout`)
- Custom `@login_required` decorator defined in `main.py` checks session state and redirects to login

### Session-Based Authentication
- User data stored in Flask session: `session["user"] = {"email": ..., "id": ...}`
- Session cleared on logout
- No JWT tokens stored client-side; Supabase access tokens available in login response but not persisted
- Session configuration in `app/config.py` includes `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`

### Template Structure
- `templates/base.html` - Base template with flash message handling
- `templates/index.html` - Landing page
- `templates/application.html` - Protected page with Gemini prompt interface
- `templates/auth/` - Login and registration forms

### Configuration Management
- `app/config.py` - Loads environment variables via `python-dotenv`
- All config values accessible via `app.config` dictionary
- Environment variables loaded from `.env` for local development, Vercel env vars in production

## Important Patterns

### Service Access Pattern
Services are accessed via `current_app` within request context:
```python
from flask import current_app

result = current_app.supabase_service.login_user(email, password)
response = current_app.gemini_service.generate_response(prompt)
```

### Error Handling Pattern
Services return result objects rather than raising exceptions:
- SupabaseService returns `SupabaseResult(success, data, error)`
- Check `result.success` before accessing `result.data`
- Display `result.error` to users via flash messages

### Vercel Routing
- `vercel.json` routes all traffic `/(.*)` to `api/index.py`
- Python runtime set to `python3.11`
- All routes handled by Flask app, no static file routing configuration needed

## Database Schema

The application uses two main tables in Supabase:

### conversations table
Stores chat history between users and Gemini AI:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key to auth.users)
- `prompt` (TEXT) - User's input
- `response` (TEXT) - Gemini's response
- `created_at` (TIMESTAMP)

### user_profiles table
Extended user metadata beyond Supabase Auth:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key to auth.users)
- `display_name` (TEXT)
- `preferences` (JSONB)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### Row Level Security (RLS)
Both tables have RLS policies ensuring users can only access their own data. Policies check `auth.uid() = user_id` for all operations.

### Database Setup
Run `schema.sql` in Supabase SQL Editor to create tables and RLS policies. See `SETUP.md` for detailed migration instructions.

## Required Environment Variables
- `FLASK_SECRET_KEY` - Session signing (required)
- `SUPABASE_URL` - Supabase project URL (currently: https://jzinycxsxveexsghzcob.supabase.co)
- `SUPABASE_ANON_KEY` - Supabase anonymous key for client auth
- `GEMINI_API_KEY` - Google AI Studio API key
- `SESSION_COOKIE_SECURE` - Set to `true` in production

## Data Persistence Flow

When a user submits a prompt on `/application`:
1. Route retrieves `user_id` from Flask session
2. Gemini service generates response
3. Route calls `supabase_service.save_conversation(user_id, prompt, response)`
4. Conversation stored in database with RLS ensuring user ownership
5. Route reloads conversations via `get_user_conversations(user_id, limit=20)`
6. Template displays both current response and conversation history
