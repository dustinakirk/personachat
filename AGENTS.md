# Repository Guidelines

## Project Structure & Module Organization
PersonaChat targets Vercel’s serverless Python runtime. `api/index.py` stays minimal and simply calls `app.create_app()`. The `app/` package holds configuration, blueprints in `routes/`, shared services (Supabase, Gemini, persona, conversation), and models—add new features as blueprints plus companion services. UI lives in `templates/` and `static/`. Database work belongs in `supabase/migrations/` with reference SQL in `schema.sql` or `migrate_to_v1.sql`. Operational scripts and smoke tests (`test_v1_features.py`, `test_gemini_models.py`, `scripts/`) stay at the repo root.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` — standard dev/CI environment.
- `cp .env.example .env` then fill `FLASK_SECRET_KEY`, Supabase keys, `GEMINI_API_KEY`, and set `SESSION_COOKIE_SECURE=true` for prod-like runs.
- `python api/index.py` — launches the Flask dev server on `0.0.0.0:5006`; Vercel overrides the port in production.
- `supabase migration new <slug>` followed by `supabase db push` — create and verify schema changes before committing app code.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and light type hints as in `app/__init__.py`. Keep files `snake_case`, classes `PascalCase`, blueprint instances `<feature>_bp`, and route functions verb-first. Place reusable API logic in `app/services/` instead of views. Match template filenames to their routes and keep shared styling in `static/css/styles.css`. Run Black (or equivalent) and group imports stdlib/third-party/local before pushing.

## Testing Guidelines
Smoke tests rely on real Supabase and Gemini credentials, so load the same `.env` used by `Config`. Run `python test_v1_features.py` after touching routes, services, or migrations to confirm tables and blueprint registration. Execute `python test_gemini_models.py` whenever Gemini defaults or model lists change to verify streaming/non-streaming calls. For unit coverage, add `pytest` modules named `test_<feature>.py` beside their code and require `python -m pytest` before merging.

## Commit & Pull Request Guidelines
History favors short, imperative subjects (“Fix UUID generation”), so keep them under ~60 characters and move context into the body. Reference related issues, list Supabase migration filenames, and explain new environment variables or scripts. Each PR should summarize user-visible impact, note the commands/tests you ran, and attach screenshots or terminal output for UI or CLI work. Keep `.env` files and secrets out of commits, and scope diffs so schema updates, refactors, and features land separately.
