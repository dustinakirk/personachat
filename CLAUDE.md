# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PersonaChat V1 is a Flask web application for creating AI-enriched personas, building relationship networks, and conducting multi-persona conversations. It's designed for Vercel serverless deployment and integrates Supabase (database/auth) and Google Gemini (AI features).

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

### Database Setup & Migrations

**Automated Migrations (Recommended):**
```bash
# Migrations run automatically via GitHub Actions when pushed to main
# See .github/workflows/migrate.yml

# To create a new migration:
supabase migration new <description>
# Edit the generated file in supabase/migrations/
# Commit and push to main - GitHub Actions will apply it automatically
```

**Manual Migration (Fallback):**
```bash
# Link to Supabase project (one-time)
supabase link --project-ref jzinycxsxveexsghzcob

# Apply migrations manually
supabase db push

# Or run SQL directly in Supabase SQL Editor:
# https://supabase.com/dashboard/project/jzinycxsxveexsghzcob/sql
```

**Database Tables:**
- user_profiles, persona_groups, personas, persona_relationships
- conversations, conversation_participants, messages
- See schema in `supabase/migrations/20251111000000_v1_migration.sql`

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
vercel env add GEMINI_DEFAULT_MODEL
vercel env add GEMINI_SYSTEM_INSTRUCTION
vercel env add SESSION_COOKIE_SECURE
```

## Architecture

### Application Factory Pattern
- **Entry Point**: `api/index.py` - Vercel serverless handler
- **Factory**: `app/__init__.py` - `create_app()` function:
  - Configures Flask app with templates/static paths
  - Initializes 4 services as app attributes
  - Registers 4 blueprints (main, personas, network, conversations)
  - Injects global context variables

### Service Layer
All services follow the Result pattern (SupabaseResult/GeminiResult) with `success`, `data`, `error` fields.

**1. SupabaseService** (`app/services/supabase_service.py`)
- Authentication: `register_user()`, `login_user()`
- Legacy conversation methods (for old `/application` route)
- Returns: `SupabaseResult` dataclass

**2. GeminiService** (`app/services/gemini_service.py`)
- **Standard Generation**: `generate_response()`, `generate_streaming_response()`
- **Persona Enrichment**: `generate_persona_enrichment(description)` - Converts free-form text to structured PersonaEnrichment
- **Suggestions**: `suggest_related_personas(focal_persona, existing_personas)` - Returns list of PersonaSuggestion objects
- **Multi-Persona Chat**:
  - `generate_persona_response(persona, user_message, chat_history, other_personas)` - Single persona response
  - `route_message_to_personas(message, participants, history)` - Determines up to 3 responders
- Returns: `GeminiResult` dataclass
- Models: gemini-2.5-flash (default), gemini-2.0-flash-exp, gemini-2.5-pro

**3. PersonaService** (`app/services/persona_service.py`)
- **Persona CRUD**: `create_persona()`, `get_persona()`, `get_personas()`, `update_persona()`, `search_personas()`, `archive_persona()`, `delete_persona()`
- **Groups**: `create_persona_group()`, `get_persona_groups()`, `update_persona_group()`, `delete_persona_group()`
- **Relationships**: `create_relationship()`, `get_persona_relationships()`, `update_relationship()`, `delete_relationship()`
- **Network Data**: `get_network_data(user_id, center_persona_id=None)` - Returns personas + relationships for visualization
- Returns: `SupabaseResult` dataclass

**4. ConversationService** (`app/services/conversation_service.py`)
- **Conversations**: `create_conversation()`, `get_conversation()`, `get_user_conversations()`, `update_conversation_title()`, `delete_conversation()`
- **Participants**: `add_participant()`, `remove_participant()`, `toggle_participant()`, `get_participants()`
- **Messages**: `add_user_message()`, `add_persona_message()`, `get_messages()`
- **Utilities**: `generate_conversation_title()`, `get_conversation_summary()`
- Returns: `SupabaseResult` dataclass

### Domain Models (`app/models.py`)
Dataclasses for type safety and structure:
- **Persona**: id, name, role, company, goals[], pains[], behaviors, tools, quotes[], tags[], archived, etc.
- **PersonaGroup**: id, name, description
- **PersonaRelationship**: from_persona_id, to_persona_id, relationship_type, label
- **Conversation**: id, title, user_id
- **Message**: id, conversation_id, persona_id (null for user), user_id (null for persona), content
- **PersonaEnrichment**: AI-generated structured data from user description
- **PersonaSuggestion**: AI-generated related persona recommendation

### Route Organization (Blueprints)

**1. main_bp** (`app/routes/main.py`) - URL prefix: `/`
- `/` - Dashboard (if logged in) or landing page
- `/application` - Legacy Gemini chat interface (kept for backward compatibility)
- `/stream` - SSE streaming endpoint (legacy)
- `/register`, `/login`, `/logout` - Authentication

**2. personas_bp** (`app/routes/personas.py`) - URL prefix: `/personas`
- `/` - Persona library with search and filters
- `/create` (GET/POST) - Create persona with AI enrichment
- `/save` (POST) - Save edited enrichment
- `/<persona_id>/edit` (GET/POST) - Edit persona
- `/<persona_id>/suggestions` - View related persona suggestions
- `/<persona_id>/accept-suggestion` (POST) - Accept suggestion and create relationship
- `/<persona_id>/archive` (POST), `/unarchive` (POST), `/delete` (POST)
- `/groups/create` (POST) - Create persona group

**3. network_bp** (`app/routes/network.py`) - URL prefix: `/network`
- `/` - Network visualization view (Cytoscape.js)
- `/data` (GET) - JSON endpoint for graph data (nodes + edges)
- `/relationships/create` (POST) - Create edge
- `/relationships/<rel_id>/update` (POST) - Update edge label/type
- `/relationships/<rel_id>/delete` (POST) - Delete edge
- `/expand/<persona_id>` (GET) - Get expansion suggestions for node

**4. conversations_bp** (`app/routes/conversations.py`) - URL prefix: `/conversations`
- `/` - List recent conversations
- `/create` (GET/POST) - Create conversation with participant selection
- `/<conv_id>` - Chat interface
- `/<conv_id>/send` (POST) - Send user message, get persona responses
- `/<conv_id>/participants/add` (POST), `/remove` (POST), `/toggle` (POST)
- `/<conv_id>/delete` (POST), `/title` (POST)

### Session-Based Authentication
- User data stored in Flask session: `session["user"] = {"email": ..., "id": ...}`
- Custom `@login_required` decorator in each blueprint
- No JWT tokens client-side; Supabase access tokens not persisted

### Template Structure

**Base & Shared**
- `templates/base.html` - Navigation updated with Personas, Network, Conversations links
- `templates/dashboard.html` - Home dashboard with quick actions, stats, recent conversations
- `templates/index.html` - Landing page (not logged in)

**Personas** (`templates/personas/`)
- `library.html` - Grid view with search, filter, archive
- `create.html` - Two-step: (1) free-form description, (2) edit AI-enriched profile
- `edit.html` - Full persona editing form
- `suggestions.html` - Related persona suggestions with accept/dismiss

**Network**
- `templates/network.html` - Cytoscape.js graph with sidebar controls and filters

**Conversations** (`templates/conversations/`)
- `list.html` - Recent conversations list
- `create.html` - Participant selection (1-5 personas)
- `chat.html` - Multi-persona chat interface with labeled messages, participant sidebar

## Database Schema

### Tables
1. **user_profiles** - Extended user metadata
2. **persona_groups** - Organize personas
3. **personas** - Persona profiles (name, role, company, goals[], pains[], behaviors, tools, quotes[], tags[], archived)
4. **persona_relationships** - Network edges (from_persona, to_persona, type, label)
5. **conversations** - Chat sessions (title, user_id)
6. **conversation_participants** - Many-to-many (conversation_id, persona_id, active)
7. **messages** - Chat messages (conversation_id, persona_id OR user_id, content)

### Row Level Security (RLS)
All tables have RLS policies ensuring users only access their own data via `auth.uid() = user_id`.

### Indexes
Created on user_id, group_id, conversation_id, persona_id, archived, updated_at for performance.

## Important Patterns

### Service Access Pattern
```python
from flask import current_app

# PersonaService example
result = current_app.persona_service.get_personas(user_id)
if result.success:
    personas = result.data.get("personas", [])
else:
    flash(result.error, "error")

# GeminiService persona enrichment
enrichment_result = current_app.gemini_service.generate_persona_enrichment(description)
if enrichment_result.success:
    enrichment = enrichment_result.data  # PersonaEnrichment object
```

### Error Handling Pattern
- Services return Result objects, never raise exceptions
- Check `result.success` before accessing `result.data`
- Display `result.error` to users via flash messages
- Frontend uses AJAX with JSON responses: `{"success": bool, "data": ..., "error": ...}`

### AI Routing Pattern
```python
# Multi-persona chat flow:
1. User sends message
2. Check for @mentions → direct to mentioned persona
3. If no mention, use route_message_to_personas() → returns persona IDs
4. Generate responses using generate_persona_response() for each selected persona
5. Save all responses to messages table
6. Return responses to frontend
```

### Network Visualization Pattern
- Backend: `/network/data` returns `{"elements": {"nodes": [...], "edges": [...]}}`
- Frontend: Cytoscape.js initializes with elements, applies styling and layout
- Interactions: Click node → show details, click edge → edit label, filters → hide/show edges

## Frontend Assets

### CSS
- `static/css/styles.css` - Dark theme with CSS variables (--bg, --panel, --text, --accent, --border)

### JavaScript (Inline in Templates)
- **Personas**: Archive/delete with undo, dynamic form fields (goals, pains, quotes)
- **Network**: Cytoscape.js initialization, filters, relationship editing, expansion
- **Conversations**: Message sending, participant toggling, title editing, transcript copying

## Common Operations

### Creating a Persona
1. User enters free-form description in `/personas/create`
2. POST triggers `gemini_service.generate_persona_enrichment()`
3. Enrichment shown in editable form
4. User submits to `/personas/save`
5. `persona_service.create_persona()` saves to DB
6. Redirect to `/personas/<id>/suggestions` for related personas

### Multi-Persona Chat
1. User selects 1-5 personas in `/conversations/create`
2. POST creates conversation + adds participants
3. Redirect to `/conversations/<id>` chat interface
4. User sends message → POST to `/conversations/<id>/send`
5. Backend routes message (checks @mention or uses AI routing)
6. Generate responses from selected personas (max 3)
7. Save all messages to DB
8. Return JSON responses to frontend
9. Page reloads to show new messages

### Network Expansion
1. User clicks "Expand Network" on a persona node
2. GET `/network/expand/<persona_id>`
3. Backend calls `gemini_service.suggest_related_personas()`
4. Returns JSON suggestions
5. User accepts → creates new persona + relationship
6. Graph refreshes

## Vercel Routing
- `vercel.json` routes all traffic `(.*)` to `api/index.py`
- Python runtime: 3.11
- All routes handled by Flask app, no static file routing config needed

## Required Environment Variables
```bash
FLASK_SECRET_KEY           # Session signing
SUPABASE_URL              # https://xxx.supabase.co
SUPABASE_ANON_KEY         # Supabase anonymous key
GEMINI_API_KEY            # Google AI Studio API key
GEMINI_DEFAULT_MODEL      # gemini-2.5-flash (default)
GEMINI_SYSTEM_INSTRUCTION # Optional AI personality
SESSION_COOKIE_SECURE     # true in production
```

## Implementation Status

### ✅ Completed Features (V1 PRD)
- Persona creation from single text area with AI enrichment
- Editable persona profiles (name, role, company, goals, pains, behaviors, tools, quotes, tags)
- Related persona suggestions with accept/dismiss
- Network visualization (Cytoscape.js with pan/zoom/drag)
- Relationship editing (add/remove edges, rename labels)
- Multi-persona chat with intelligent routing
- @mention support for directed messages
- Autosave conversations with resume functionality
- Participant management (add/remove/mute mid-chat)
- Home dashboard with recent conversations and persona library
- Search and filtering for personas
- Archive/delete personas with undo

### Known Limitations
- No streaming responses in multi-persona chat (uses standard generation)
- No real-time updates (page reloads after sending message)
- Network graph limited to ~30 nodes for readability
- Max 5 personas per conversation
- Max 3 persona responses per user message

## Data Persistence Flow

### Persona Creation
1. User description → AI enrichment → User edits → Save → Suggestions
2. All data stored in `personas` table with JSONB fields for arrays
3. Suggestions trigger `persona_relationships` table inserts when accepted

### Multi-Persona Conversation
1. Create conversation → Add participants → Send message → Route to personas → Generate responses → Save messages
2. Conversation state: `conversations` table
3. Participants: `conversation_participants` table (includes `active` flag for muting)
4. Messages: `messages` table with `persona_id` (persona message) or `user_id` (user message)

## Future Enhancements (Out of V1 Scope)
- Real-time streaming for multi-persona responses
- Collaboration/teams features
- Advanced analytics
- Complex permissions
- Share links for conversations
- Nested persona groups
- Duplicate detection and merge
- Avatar generation
- Detailed exports (CSV, JSON)
- In-line persona creation from chat (@NewPersona description)
