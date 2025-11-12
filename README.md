# PersonaChat Flask Starter

A Flask starter kit prepared for Vercel that uses Supabase for authentication/storage and Google Gemini for AI-powered responses. It includes server-rendered templates, vanilla CSS, and session-based auth.

## Features
- Flask app factory wired to Vercel's serverless Python runtime (`api/index.py`).
- Supabase service wrapper for user registration and login.
- Gemini helper for sending prompts to `gemini-pro`.
- Server-rendered templates (`templates/`) with matching CSS (`static/css/styles.css`).
- Index page, authenticated application page, registration, login, and logout flows.

## Getting Started Locally
1. **Python environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Environment variables**
   ```bash
   cp .env.example .env
   ```
   Fill in:
   - `FLASK_SECRET_KEY`: any random string for session signing.
   - `SUPABASE_URL` / `SUPABASE_ANON_KEY`: from your Supabase project settings.
   - `GEMINI_API_KEY`: Google AI Studio API key.
   - `SESSION_COOKIE_SECURE`: set `true` in production.
3. **Run the server**
   ```bash
   python api/index.py
   ```
   The app listens on `http://127.0.0.1:8000` by default.

## Supabase Setup

### Database Migrations
This project uses Supabase CLI for automated database migrations:

1. **Initial Setup** (One-time)
   - Ensure you have the Supabase CLI installed: `brew install supabase/tap/supabase`
   - Get your Supabase Access Token:
     1. Go to https://supabase.com/dashboard/account/tokens
     2. Generate a new access token
     3. Add it to your GitHub repository secrets as `SUPABASE_ACCESS_TOKEN`
   - Add your project reference to GitHub secrets as `SUPABASE_PROJECT_REF` (value: `jzinycxsxveexsghzcob`)

2. **Automated Migrations** (On Push to Main)
   - When you push changes to `supabase/migrations/**` on the main branch, GitHub Actions automatically:
     - Links to your Supabase project
     - Applies any new migration files
     - Verifies the migration succeeded
   - View migration status in the "Actions" tab of your GitHub repository

3. **Creating New Migrations**
   ```bash
   # Create a new migration file
   supabase migration new <migration_name>

   # Edit the generated file in supabase/migrations/
   # Then commit and push to trigger automated deployment
   ```

4. **Manual Migration** (If Needed)
   ```bash
   # Link to your project (one-time)
   supabase link --project-ref jzinycxsxveexsghzcob

   # Apply migrations manually
   supabase db push
   ```

### Authentication
- Create a Supabase project and enable email/password authentication
- The app uses `supabase.auth.sign_up` and `sign_in_with_password`
- User data is stored in custom tables (see schema in `supabase/migrations/`)

## Gemini Notes
- Enable the Google Generative AI API and create an API key in Google AI Studio.
- Update `GEMINI_API_KEY` and redeploy/restart to refresh the client configuration.

## Deploying on Vercel
1. Install the Vercel CLI and log in: `npm i -g vercel && vercel login`.
2. Run `vercel` once to create the project, then `vercel deploy --prod` when ready.
3. Set environment variables via the Vercel dashboard or CLI:
   ```bash
   vercel env add FLASK_SECRET_KEY
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_ANON_KEY
   vercel env add GEMINI_API_KEY
   vercel env add SESSION_COOKIE_SECURE
   ```
4. The provided `vercel.json` routes all traffic to `api/index.py`, which exposes the Flask app factory.

## Next Steps
- Add Supabase database tables for storing persona/application data.
- Extend the Gemini integration with streaming responses or multi-turn conversations.
- Write unit tests (e.g., pytest) for the Supabase and Gemini service wrappers.
