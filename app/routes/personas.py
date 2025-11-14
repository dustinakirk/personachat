"""
Personas Blueprint - Routes for persona management

Handles persona creation, enrichment, editing, library, and related suggestions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify, g
from functools import wraps

from app.models import PersonaEnrichment, Persona
from app.decorators import requires_services, requires_persona_service

personas_bp = Blueprint("personas", __name__, url_prefix="/personas")


def login_required(f):
    """Decorator to require login for persona routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access personas.", "error")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# PERSONA LIBRARY & LISTING
# ============================================================================

@personas_bp.route("/")
@login_required
@requires_services
def library():
    """Display persona library with search and filtering"""
    user_id = session["user"]["id"]
    search_query = request.args.get("q", "").strip()

    # Pagination for conversations
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # Get personas (with optional search)
    if search_query:
        result = g.persona_service.search_personas(user_id, search_query)
    else:
        result = g.persona_service.get_personas(user_id)

    if result.success:
        personas = result.data.get("personas", [])
    else:
        personas = []
        flash(f"Error loading personas: {result.error}", "error")

    # Get paginated conversations with participants
    conversations = []
    total_conversations = 0
    if g.conversation_service:
        # Get total count first
        total_result = g.conversation_service.get_user_conversations(user_id, limit=1000)
        if total_result.success:
            total_conversations = len(total_result.data.get("conversations", []))

        # Get paginated conversations
        conv_result = g.conversation_service.get_user_conversations(user_id, limit=per_page)
        if conv_result.success:
            conversations_raw = conv_result.data.get("conversations", [])

            # Apply manual pagination (since service doesn't support offset)
            conversations_raw = conversations_raw[offset:offset + per_page]

            # Enrich each conversation with participant data
            for conv in conversations_raw:
                # Get participants for this conversation
                participants_result = g.conversation_service.get_participants(conv["id"])
                if participants_result.success:
                    conv["participants"] = participants_result.data.get("participants", [])
                else:
                    conv["participants"] = []
                conversations.append(conv)

    # Get persona count for showing getting started guide
    persona_count = len(personas)

    # Get the newly created persona ID if present
    created_persona_id = request.args.get("created")

    return render_template(
        "personas/library.html",
        personas=personas,
        search_query=search_query,
        conversations=conversations,
        total_conversations=total_conversations,
        page=page,
        per_page=per_page,
        persona_count=persona_count,
        created_persona_id=created_persona_id
    )


@personas_bp.route("/api/list", methods=["GET"])
@login_required
@requires_persona_service
def api_list():
    """AJAX endpoint to fetch all personas as JSON (for persona selector)"""
    user_id = session["user"]["id"]
    search_query = request.args.get("q", "").strip()

    # Get personas (with optional search)
    if search_query:
        result = g.persona_service.search_personas(user_id, search_query)
    else:
        result = g.persona_service.get_personas(user_id)

    if result.success:
        # Convert Persona objects to dicts for JSON serialization
        personas = result.data.get("personas", [])
        personas_dict = [p.to_dict() for p in personas]
        return jsonify({
            "success": True,
            "personas": personas_dict
        })
    else:
        return jsonify({
            "success": False,
            "error": result.error
        }), 500


@personas_bp.route("/api/<persona_id>", methods=["GET"])
@login_required
@requires_persona_service
def api_get(persona_id):
    """AJAX endpoint to fetch a single persona as JSON"""
    user_id = session["user"]["id"]

    result = g.persona_service.get_persona(persona_id)

    if not result.success:
        return jsonify({
            "success": False,
            "error": result.error
        }), 404

    persona = result.data

    # Verify ownership
    if persona.user_id != user_id:
        return jsonify({
            "success": False,
            "error": "Permission denied"
        }), 403

    return jsonify({
        "success": True,
        "persona": {
            "id": persona.id,
            "name": persona.name,
            "role": persona.role,
            "company": persona.company,
            "age_stage": persona.age_stage,
            "goals": persona.goals or [],
            "pains": persona.pains or [],
            "behaviors": persona.behaviors,
            "tools": persona.tools,
            "quotes": persona.quotes or [],
            "tags": persona.tags or [],
            "notes": persona.notes
        }
    })


@personas_bp.route("/api/enrich", methods=["POST"])
@login_required
@requires_services
def api_enrich():
    """AJAX endpoint to enrich a persona description"""
    user_id = session["user"]["id"]

    try:
        data = request.get_json()
        description = data.get("description", "").strip()

        if not description:
            return jsonify({
                "success": False,
                "error": "Please provide a persona description."
            }), 400

        # Fetch existing personas for relationship detection
        existing_personas = []
        if g.persona_service:
            personas_result = g.persona_service.get_personas(user_id)
            if personas_result.success:
                existing_personas = personas_result.data.get("personas", [])

        # Generate AI enrichment
        enrichment_result = current_app.gemini_service.generate_persona_enrichment(
            description,
            existing_personas=existing_personas
        )

        if not enrichment_result.success:
            return jsonify({
                "success": False,
                "error": enrichment_result.error
            }), 500

        enrichment = enrichment_result.data

        # DEBUG: Log enrichment data
        print(f"[API ENRICH] Enrichment custom_fields: {enrichment.custom_fields}")
        print(f"[API ENRICH] Custom fields count: {len(enrichment.custom_fields) if enrichment.custom_fields else 0}")

        # Convert enrichment to dict for JSON response
        return jsonify({
            "success": True,
            "data": {
                "name": enrichment.name,
                "role": enrichment.role,
                "company": enrichment.company,
                "age_stage": enrichment.age_stage,
                "goals": enrichment.goals,
                "pains": enrichment.pains,
                "behaviors": enrichment.behaviors,
                "tools": enrichment.tools,
                "quotes": enrichment.quotes,
                "tags": enrichment.tags,
                "custom_fields": enrichment.custom_fields,
                "suggested_relationships": [
                    {
                        "persona_id": rel.persona_id,
                        "persona_name": rel.persona_name,
                        "relationship_type": rel.relationship_type,
                        "shared_context": rel.shared_context,
                        "interaction_style": rel.interaction_style
                    }
                    for rel in (enrichment.suggested_relationships or [])
                ]
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@personas_bp.route("/api/create", methods=["POST"])
@login_required
@requires_persona_service
def api_create():
    """AJAX endpoint to create a persona from enriched data"""
    user_id = session["user"]["id"]

    try:
        data = request.get_json()

        # Extract data
        name = data.get("name", "").strip()
        role = data.get("role", "").strip()
        company = data.get("company", "").strip()
        age_stage = data.get("age_stage", "").strip()
        goals = [g.strip() for g in data.get("goals", []) if g.strip()]
        pains = [p.strip() for p in data.get("pains", []) if p.strip()]
        behaviors = data.get("behaviors", "").strip()
        tools = data.get("tools", "").strip()
        quotes = [q.strip() for q in data.get("quotes", []) if q.strip()]
        tags_str = data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if isinstance(tags_str, str) else tags_str
        avatar_emoji = data.get("avatar_emoji", "").strip() if data.get("avatar_emoji") else None
        avatar_color = data.get("avatar_color", "").strip() if data.get("avatar_color") else None
        custom_fields = data.get("custom_fields", {})

        # DEBUG: Log avatar values from JSON
        print(f"[API CREATE] Avatar from JSON - emoji: '{avatar_emoji}', color: '{avatar_color}'")

        if not name:
            return jsonify({
                "success": False,
                "error": "Persona name is required."
            }), 400

        # Create PersonaEnrichment
        enrichment = PersonaEnrichment(
            name=name,
            role=role,
            company=company or None,
            age_stage=age_stage or None,
            goals=goals,
            pains=pains,
            behaviors=behaviors or None,
            tools=tools or None,
            quotes=quotes,
            tags=tags,
            avatar_emoji=avatar_emoji,
            avatar_color=avatar_color,
            custom_fields=custom_fields
        )

        # DEBUG: Log enrichment avatar values
        print(f"[API CREATE] PersonaEnrichment created - emoji: '{enrichment.avatar_emoji}', color: '{enrichment.avatar_color}'")

        # Save persona
        result = g.persona_service.create_persona(user_id, enrichment)

        if result.success:
            persona_id = result.data.get("id")
            persona_data = result.data

            return jsonify({
                "success": True,
                "data": {
                    "id": persona_id,
                    "name": persona_data.get("name"),
                    "role": persona_data.get("role"),
                    "company": persona_data.get("company")
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@personas_bp.route("/api/<persona_id>", methods=["PUT"])
@login_required
@requires_persona_service
def api_update(persona_id):
    """AJAX endpoint to update a persona"""
    user_id = session["user"]["id"]

    try:
        # Verify ownership
        persona_result = g.persona_service.get_persona(persona_id)
        if not persona_result.success:
            return jsonify({
                "success": False,
                "error": "Persona not found"
            }), 404

        persona = persona_result.data
        if persona.user_id != user_id:
            return jsonify({
                "success": False,
                "error": "Permission denied"
            }), 403

        # Extract data
        data = request.get_json()
        name = data.get("name", "").strip()
        role = data.get("role", "").strip()
        company = data.get("company", "").strip()
        age_stage = data.get("age_stage", "").strip()
        goals = [g.strip() for g in data.get("goals", []) if g.strip()]
        pains = [p.strip() for p in data.get("pains", []) if p.strip()]
        behaviors = data.get("behaviors", "").strip()
        tools = data.get("tools", "").strip()
        quotes = [q.strip() for q in data.get("quotes", []) if q.strip()]
        tags_str = data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if isinstance(tags_str, str) else tags_str
        notes = data.get("notes", "").strip()
        avatar_emoji = data.get("avatar_emoji", "").strip() if data.get("avatar_emoji") else None
        avatar_color = data.get("avatar_color", "").strip() if data.get("avatar_color") else None
        custom_fields = data.get("custom_fields", {})

        # DEBUG: Log avatar values from JSON
        print(f"[API UPDATE] Avatar from JSON - emoji: '{avatar_emoji}', color: '{avatar_color}'")

        if not name:
            return jsonify({
                "success": False,
                "error": "Persona name is required."
            }), 400

        # Update persona
        updates = {
            "name": name,
            "role": role,
            "company": company or None,
            "age_stage": age_stage or None,
            "goals": goals,
            "pains": pains,
            "behaviors": behaviors or None,
            "tools": tools or None,
            "quotes": quotes,
            "tags": tags,
            "notes": notes or None,
            "avatar_emoji": avatar_emoji,
            "avatar_color": avatar_color,
            "custom_fields": custom_fields
        }

        # DEBUG: Log updates dict with avatar values
        print(f"[API UPDATE] Updates dict - emoji: '{updates['avatar_emoji']}', color: '{updates['avatar_color']}'")

        result = g.persona_service.update_persona(persona_id, updates)

        if result.success:
            return jsonify({
                "success": True,
                "data": {
                    "id": persona_id,
                    "name": name
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# PERSONA CREATION
# ============================================================================

@personas_bp.route("/create", methods=["GET", "POST"])
@login_required
@requires_services
def create():
    """Create a new persona with AI enrichment and relationship detection"""
    user_id = session["user"]["id"]

    if request.method == "GET":
        return render_template("personas/create.html")

    # Handle POST - create persona
    description = request.form.get("description", "").strip()

    if not description:
        flash("Please provide a persona description.", "error")
        return render_template("personas/create.html")

    # Fetch existing personas for relationship detection
    existing_personas = []
    if g.persona_service:
        personas_result = g.persona_service.get_personas(user_id)
        if personas_result.success:
            existing_personas = personas_result.data.get("personas", [])

    # Generate AI enrichment with existing personas context
    enrichment_result = current_app.gemini_service.generate_persona_enrichment(
        description,
        existing_personas=existing_personas
    )

    if not enrichment_result.success:
        flash(f"AI enrichment failed: {enrichment_result.error}", "error")
        return render_template("personas/create.html", description=description)

    enrichment = enrichment_result.data

    # DEBUG: Log enrichment data before rendering template
    print(f"[CREATE ROUTE] Rendering template with custom_fields: {enrichment.custom_fields}")
    print(f"[CREATE ROUTE] Will show custom fields section: {bool(enrichment.custom_fields and len(enrichment.custom_fields) > 0)}")

    # Show enrichment for user editing (including suggested relationships)
    return render_template(
        "personas/create.html",
        enrichment=enrichment,
        description=description
    )


@personas_bp.route("/save", methods=["POST"])
@login_required
@requires_persona_service
def save():
    """Save a persona after enrichment (with user edits and relationships)"""
    user_id = session["user"]["id"]

    # Extract form data
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    company = request.form.get("company", "").strip()
    age_stage = request.form.get("age_stage", "").strip()
    goals = [g.strip() for g in request.form.getlist("goals[]") if g.strip()]
    pains = [p.strip() for p in request.form.getlist("pains[]") if p.strip()]
    behaviors = request.form.get("behaviors", "").strip()
    tools = request.form.get("tools", "").strip()
    quotes = [q.strip() for q in request.form.getlist("quotes[]") if q.strip()]
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    avatar_emoji = request.form.get("avatar_emoji", "").strip()
    avatar_color = request.form.get("avatar_color", "").strip()

    # DEBUG: Log avatar values from form
    print(f"[PERSONA SAVE] Avatar extracted from form - emoji: '{avatar_emoji}', color: '{avatar_color}'")

    # Extract accepted relationships (checkboxes)
    accepted_rel_ids = request.form.getlist("relationships[]")

    if not name:
        flash("Persona name is required.", "error")
        return redirect(url_for("personas.create"))

    # Create PersonaEnrichment from form data
    enrichment = PersonaEnrichment(
        name=name,
        role=role,
        company=company or None,
        age_stage=age_stage or None,
        goals=goals,
        pains=pains,
        behaviors=behaviors or None,
        tools=tools or None,
        quotes=quotes,
        tags=tags,
        avatar_emoji=avatar_emoji or None,
        avatar_color=avatar_color or None
    )

    # DEBUG: Log enrichment avatar values
    print(f"[PERSONA SAVE] PersonaEnrichment created - emoji: '{enrichment.avatar_emoji}', color: '{enrichment.avatar_color}'")

    # Save persona
    result = g.persona_service.create_persona(user_id, enrichment)

    if result.success:
        persona_id = result.data.get("id")

        # Create relationships if any were accepted
        if accepted_rel_ids:
            relationships_to_create = []
            for rel_id in accepted_rel_ids:
                # Extract relationship data from hidden form fields
                rel_type = request.form.get(f"rel_type_{rel_id}", "colleague")
                shared_context = request.form.get(f"rel_context_{rel_id}", "")
                interaction_style = request.form.get(f"rel_style_{rel_id}", "")

                relationships_to_create.append({
                    "persona_id": rel_id,
                    "relationship_type": rel_type,
                    "shared_context": shared_context,
                    "interaction_style": interaction_style
                })

            # Create relationships (bidirectional)
            if relationships_to_create:
                # Create outgoing relationships
                rel_result = g.persona_service.create_relationships_bulk(
                    user_id, persona_id, relationships_to_create
                )

                # Create reverse relationships for bidirectional
                reverse_relationships = []
                for rel in relationships_to_create:
                    reverse_relationships.append({
                        "persona_id": persona_id,
                        "relationship_type": rel["relationship_type"],
                        "shared_context": rel.get("shared_context", ""),
                        "interaction_style": rel.get("interaction_style", "")
                    })

                for rel in relationships_to_create:
                    g.persona_service.create_relationships_bulk(
                        user_id, rel["persona_id"], [{
                            "persona_id": persona_id,
                            "relationship_type": rel["relationship_type"],
                            "shared_context": rel.get("shared_context", ""),
                            "interaction_style": rel.get("interaction_style", "")
                        }]
                    )

        flash(f"Persona '{name}' created successfully!", "success")
        return redirect(url_for("personas.library", created=persona_id))
    else:
        error_msg = result.error
        # Check if it's an RLS/authentication error
        if isinstance(error_msg, dict) and error_msg.get('code') == '42501':
            flash("Your session may have expired. Please log out and log back in to continue.", "error")
        else:
            flash(f"Error saving persona: {error_msg}", "error")
        return redirect(url_for("personas.create"))


# ============================================================================
# PERSONA EDITING
# ============================================================================

@personas_bp.route("/<persona_id>/edit", methods=["GET", "POST"])
@login_required
@requires_persona_service
def edit(persona_id):
    """Edit an existing persona"""
    user_id = session["user"]["id"]

    # Get persona
    persona_result = g.persona_service.get_persona(persona_id)
    if not persona_result.success:
        flash("Persona not found.", "error")
        return redirect(url_for("personas.library"))

    persona = persona_result.data

    # Verify ownership
    if persona.user_id != user_id:
        flash("You don't have permission to edit this persona.", "error")
        return redirect(url_for("personas.library"))

    if request.method == "GET":
        return render_template("personas/edit.html", persona=persona)

    # Handle POST - update persona
    # DEBUG: Log raw form values for avatar
    raw_emoji = request.form.get("avatar_emoji", "")
    raw_color = request.form.get("avatar_color", "")
    print(f"[PERSONA EDIT] Raw avatar from form - emoji: '{raw_emoji}', color: '{raw_color}'")

    updates = {
        "name": request.form.get("name", "").strip(),
        "role": request.form.get("role", "").strip(),
        "company": request.form.get("company", "").strip() or None,
        "age_stage": request.form.get("age_stage", "").strip() or None,
        "goals": [g.strip() for g in request.form.getlist("goals[]") if g.strip()],
        "pains": [p.strip() for p in request.form.getlist("pains[]") if p.strip()],
        "behaviors": request.form.get("behaviors", "").strip() or None,
        "tools": request.form.get("tools", "").strip() or None,
        "quotes": [q.strip() for q in request.form.getlist("quotes[]") if q.strip()],
        "tags": [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()],
        "notes": request.form.get("notes", "").strip() or None,
        "avatar_emoji": request.form.get("avatar_emoji", "").strip() or None,
        "avatar_color": request.form.get("avatar_color", "").strip() or None
    }

    # DEBUG: Log processed avatar values in updates dict
    print(f"[PERSONA EDIT] Updates dict - emoji: '{updates['avatar_emoji']}', color: '{updates['avatar_color']}'")

    if not updates["name"]:
        flash("Persona name is required.", "error")
        return redirect(url_for("personas.edit", persona_id=persona_id))

    result = g.persona_service.update_persona(persona_id, updates)

    if result.success:
        flash(f"Persona '{updates['name']}' updated successfully!", "success")
        return redirect(url_for("personas.library"))
    else:
        flash(f"Error updating persona: {result.error}", "error")
        return redirect(url_for("personas.edit", persona_id=persona_id))


# ============================================================================
# PERSONA ACTIONS (Archive, Delete)
# ============================================================================

@personas_bp.route("/<persona_id>/archive", methods=["POST"])
@login_required
@requires_persona_service
def archive(persona_id):
    """Archive a persona (soft delete)"""
    result = g.persona_service.archive_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@personas_bp.route("/<persona_id>/unarchive", methods=["POST"])
@login_required
@requires_persona_service
def unarchive(persona_id):
    """Unarchive a persona"""
    result = g.persona_service.unarchive_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@personas_bp.route("/<persona_id>/delete", methods=["POST"])
@login_required
@requires_persona_service
def delete(persona_id):
    """Permanently delete a persona"""
    result = g.persona_service.delete_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500
