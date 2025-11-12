# Persona Chat — V1 PRD (Core Functionality)

*Date:* Nov 11, 2025

## 1) Summary

Persona Chat lets a user quickly create personas from a single free‑form input, see related personas as a simple network, and chat with one or more personas at once. V1 focuses on fast capture, light curation, clear network visualization, and reliable multi‑persona conversations with saved history.

## 2) In Scope (V1)

* **Persona groups & personas**: create from a single text area, AI‑enrich into an editable profile, save to a group.
* **Related persona suggestions**: after saving a persona, show a short list of suggested personas to add; user accepts/dismisses.
* **Network visualization**: display personas as nodes with labeled relationships; pan/zoom/drag, click to open/edit a persona; expand suggestions from any node.
* **Multi‑persona chat**: start a chat with selected personas; relevant personas reply first, others respond if appropriate; label each reply by speaker; personas are aware of each other; autosave and resume.
* **Home**: recent conversations, quick create persona, persona library with search and remove (archive/delete) to reduce clutter.

**Out of Scope (V1)**: collaboration/teams, advanced analytics, complex permissions, deep customization of AI prompts, share links, nested groups, duplicate‑merge, avatars generation, detailed exports beyond copy/save.

## 3) Core User Flows

### A. Home

1. Land on **Home** showing **Recent Conversations** and **Persona Library**.
2. Actions: **Create Persona**, **Start Chat**, **Open Network**.
3. Remove personas via archive/delete (with confirm + undo).

**Accept**

* See last 5–10 conversations with timestamps; open resumes.
* Create persona from Home in one step.
* Remove personas to declutter.

### B. Create & Enrich Persona (single text area)

1. Select or create a **Persona Group**.
2. Enter free‑form description (anything the user knows).
3. Click **Create Persona** → AI returns an editable structured draft.
4. User edits and **Saves**.
5. Show **Related Persona Suggestions** with short rationales; user accepts/dismisses.

**Accept**

* Only one required field (description).
* Enriched draft is editable before save; changes persist.
* At least 3 suggestions when context allows.

### C. Network View

1. Open a persona to enter **Network View** centered on that persona.
2. Pan/zoom/drag; nodes show name + role; edges show relationship label.
3. Click a node to open a **Persona Card** (inline editing of key fields).
4. Use **Expand Network** on any node to fetch more suggestions; accept/dismiss.
5. Optional filters: internal/external, relationship type.

**Accept**

* Add/remove nodes and edges; rename relationship labels.
* Layout remains readable with up to ~30 nodes.

### D. Start & Conduct a Multi‑Persona Chat

1. From Home or Network, click **Start Chat**.
2. **Select participants** (1–5 personas).
3. Type a message; optionally *@direct* a persona.
4. **Reply routing**: if directed, that persona responds first; otherwise the most relevant persona replies, followed by others if appropriate (max 3 per turn).
5. Personas may reference prior messages and each other; user can toggle participants on/off mid‑chat.
6. Chat **autosaves**; appears in Recent Conversations; **Resume** opens the same session.

**Accept**

* Each reply is clearly labeled with persona name/avatar placeholder.
* History is preserved and used for context.
* User can copy a message or the whole transcript.

## 4) Functional Requirements

### 4.1 Persona

* **Input**: one text area + (optional) group.
* **Output (editable)**: name/label, role/title, company/context, 3 goals, 3 pains, behaviors/traits, tools/systems, key stakeholders, 1–2 quotes, tags/notes.
* **Actions**: save, edit, move to group, archive/delete with undo.

### 4.2 Related Suggestions & Relationships

* **Suggestions panel** shows: name/role, why suggested, relation to focal persona.
* **Edges** (labels): manager, peer, collaborator, vendor, customer, stakeholder, family/friend.
* **User controls**: accept/dismiss suggestions; add/edit/remove edges manually.

### 4.3 Network Visualization

* **Interactions**: pan, zoom, drag nodes; click to open persona card; expand suggestions.
* **Display**: node = persona (name, role, group color/badge); edge = relationship label.
* **Filters**: relationship type, internal vs external.

### 4.4 Chat

* **Participants**: multi‑select personas per conversation; toggle during session.
* **Composer**: free text, supports *@direct*.
* **Routing**: relevant persona(s) respond; cap at 3 replies per user turn to avoid noise.
* **Context**: use recent chat turns for continuity; avoid repetition.
* **Persistence**: autosave transcript and participants; list in Recent Conversations; resume anytime.

### 4.5 Home & Library

* **Recent Conversations**: open/resume; show participants and last message time.
* **Persona Library**: list with search, group filter, remove/archive, move between groups.
* **Quick Create Persona** from Home.

## 5) Content Model (User‑Visible)

**Persona**: Name, Role/Title, Company/Context, Age/Stage (optional), Goals (3), Pains (3), Behaviors/Traits, Tools/Systems, Stakeholders (links), Quotes (1–2), Notes/Tags, Group.
**Relationship**: Type/Label, Direction (optional), Notes.
**Conversation**: Title, Participants, Messages (speaker, text, time), Summary (auto short), Pinned facts (optional).

## 6) Edge Cases & Safeguards

* **Ambiguous input** → show 2–3 enrichment variants; user selects one.
* **Over‑dense graph** → limit initial expansion; focus mode around selected node.
* **AI timeout/failure** → keep raw input as Draft; allow retry.
* **Irrelevant persona replies** → user can hide a reply or temporarily mute a persona.

## 7) Success Metrics (V1)

* Median time: input → saved persona < 60s.
* ≥60% of personas result in at least one accepted related suggestion.
* ≥50% of chats include more than one persona reply at least once.
* Week‑1 return rate: user resumes a conversation or opens Network View.

---

## 8) Implementation Status

### ✅ Fully Implemented Features

#### A. Home & Dashboard
- [x] Dashboard view with quick actions (Create Persona, Start Conversation, View Network, Library)
- [x] Recent conversations list (5 most recent) with resume functionality
- [x] Persona count statistics
- [x] Quick navigation to all major features
- [x] Landing page for non-authenticated users

#### B. Persona Creation & Enrichment
- [x] Single textarea for free-form persona description
- [x] AI-powered enrichment via Gemini API (generates structured profile)
- [x] Editable enrichment form with all fields: name, role, company, age/stage, goals (3), pains (3), behaviors, tools, quotes (1-2), tags
- [x] Optional persona group selection/creation
- [x] Persona save to database with JSONB support for arrays
- [x] Related persona suggestions (3 suggestions) after saving
- [x] Suggestion acceptance creates new persona + relationship automatically
- [x] Suggestion dismissal functionality

#### C. Persona Library & Management
- [x] Grid view of all personas with cards showing name, role, company, goals preview, tags
- [x] Search functionality (searches name, role, company fields)
- [x] Group filter dropdown
- [x] Archive persona (soft delete with undo notification)
- [x] Unarchive persona
- [x] Permanent delete persona
- [x] Edit persona (full form with all fields)
- [x] Persona groups creation and management

#### D. Network Visualization
- [x] Cytoscape.js integration for interactive graph
- [x] Pan, zoom, drag interactions
- [x] Nodes display persona name and role
- [x] Edges display relationship labels (manager, peer, collaborator, vendor, customer, stakeholder, family, friend)
- [x] Click node to view persona details in sidebar
- [x] Click edge to edit relationship label
- [x] Relationship type filters (checkbox filters for all 7 types)
- [x] Expand network suggestions from any node
- [x] Edit persona directly from network view
- [x] Add/remove relationships manually
- [x] Auto-layout with COSE algorithm (readable up to ~30 nodes)
- [x] Focus mode when centered on specific persona

#### E. Multi-Persona Chat
- [x] Conversation creation with participant selection (1-5 personas)
- [x] Chat interface with labeled messages (persona name + role)
- [x] User messages vs persona messages clearly differentiated
- [x] @mention support for directed messages (e.g., "@Sarah can you help?")
- [x] AI-powered routing (selects up to 3 relevant personas to respond)
- [x] Personas aware of each other in responses
- [x] Chat history context (last 10 messages) used for continuity
- [x] Participant sidebar with active/muted status
- [x] Toggle participants on/off mid-conversation (mute/unmute)
- [x] Add participants mid-conversation
- [x] Remove participants mid-conversation
- [x] Autosave all messages to database
- [x] Resume conversations from list
- [x] Conversation title editing
- [x] Copy transcript to clipboard
- [x] Conversation deletion

#### F. Authentication & User Management
- [x] Email/password registration via Supabase Auth
- [x] Email/password login
- [x] Session-based authentication
- [x] Logout functionality
- [x] Email verification flow
- [x] Row Level Security (RLS) on all tables

### 🟡 Partially Implemented / Known Limitations

#### Network Visualization
- [x] Basic filters implemented (relationship type checkboxes)
- [ ] Internal vs External filter (not implemented - would require adding `internal` flag to personas)
- [ ] Group color/badge on nodes (nodes use uniform styling, group info available but not visually represented)

#### Chat
- [ ] Streaming responses in multi-persona chat (uses standard generation, not SSE)
- [ ] Real-time updates (page reloads after sending message instead of live updates)
- [ ] Hide individual replies or mute specific personas mid-turn (can toggle for future turns)

#### Persona Management
- [ ] Move persona between groups (edit form allows changing group, but no drag-and-drop)
- [ ] Bulk operations (no multi-select for batch archive/delete)

### ❌ Not Implemented (Out of V1 Scope)

#### Edge Cases & Advanced Features
- [ ] Ambiguous input with multiple enrichment variants (currently shows single enrichment)
- [ ] AI retry mechanism on enrichment failure (user must re-submit description)
- [ ] Conversation summary auto-generation (title is "New Conversation" or manually set)
- [ ] Pinned facts in conversations
- [ ] Avatar generation for personas
- [ ] Detailed exports (CSV, JSON) - only copy transcript implemented

#### Out of Scope V1 Features
- [ ] Collaboration/teams features
- [ ] Advanced analytics
- [ ] Complex permissions
- [ ] Deep customization of AI prompts (system instructions only)
- [ ] Share links for conversations
- [ ] Nested persona groups
- [ ] Duplicate persona detection and merge
- [ ] In-line persona creation from chat (@NewPersona description)

### 🐛 Known Issues & Edge Cases

1. **Network Density**: Graph becomes cluttered with >30 nodes (as expected, per PRD)
2. **Message Latency**: Multi-persona responses can take 10-30 seconds depending on number of responders (sequential generation)
3. **Form Validation**: Goals/pains fields allow empty strings (no client-side validation)
4. **Relationship Bidirectionality**: Relationships are unidirectional (A → B doesn't create B → A)
5. **Search Limitations**: Search is simple string matching, no fuzzy search or tag-based filtering
6. **Mobile Responsiveness**: Network graph and chat interface optimized for desktop, mobile experience is functional but not ideal

### 📊 PRD Acceptance Criteria Status

| Flow | Acceptance Criteria | Status |
|------|---------------------|--------|
| **A. Home** | See last 5-10 conversations ✓ | ✅ Implemented (5 shown) |
| | Create persona from Home ✓ | ✅ Implemented |
| | Remove personas ✓ | ✅ Archive with undo |
| **B. Create Persona** | Only one required field ✓ | ✅ Description only |
| | Editable before save ✓ | ✅ Full edit form |
| | At least 3 suggestions ✓ | ✅ Always 3 suggestions |
| **C. Network** | Add/remove nodes & edges ✓ | ✅ Full CRUD |
| | Rename relationship labels ✓ | ✅ Click edge to edit |
| | Readable up to ~30 nodes ✓ | ✅ COSE layout |
| **D. Chat** | Labeled replies ✓ | ✅ Name + role shown |
| | History preserved ✓ | ✅ All messages saved |
| | Copy transcript ✓ | ✅ Copy button |

### 🚀 Next Steps for Production

1. **Database Migration**: Run `schema.sql` in Supabase SQL Editor to create new tables
2. **Environment Variables**: Set all required env vars in Vercel (GEMINI_API_KEY, SUPABASE_URL, etc.)
3. **Testing**: Manual testing of all user flows with real personas and conversations
4. **Performance Optimization**: Consider caching persona data, adding DB indexes for common queries
5. **Error Handling**: Add user-friendly error messages for AI failures, network errors
6. **Mobile Optimization**: Responsive design improvements for network graph and chat

### 📝 Implementation Notes

**Technology Stack:**
- Backend: Flask (Python 3.11), Supabase (PostgreSQL + Auth), Google Gemini API
- Frontend: Jinja2 templates, vanilla JavaScript, Cytoscape.js (network viz)
- Deployment: Vercel serverless
- Database: PostgreSQL with RLS, JSONB for array fields

**Architecture Highlights:**
- 4 Flask blueprints (main, personas, network, conversations)
- 4 service classes (Supabase, Gemini, Persona, Conversation)
- 7 database tables with Row Level Security
- Result pattern for error handling (no exceptions thrown)
- Session-based authentication (no JWT client-side)

**File Structure:**
- `app/routes/`: 4 blueprint modules
- `app/services/`: 4 service modules
- `app/models.py`: Domain dataclasses
- `templates/`: 12+ Jinja2 templates
- `schema.sql`: Complete database schema with RLS

**Total Implementation:**
- ~2,800 lines of Python (backend)
- ~1,800 lines of Jinja2/HTML (templates)
- ~1,200 lines of JavaScript (inline)
- ~500 lines of SQL (schema)
- **Total: ~6,300 lines of code**
