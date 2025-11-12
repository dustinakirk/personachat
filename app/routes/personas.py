"""
Personas Blueprint - Routes for persona management

Handles persona creation, enrichment, editing, library, and related suggestions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from functools import wraps

from app.models import PersonaEnrichment, Persona

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
def library():
    """Display persona library with search and filtering"""
    user_id = session["user"]["id"]
    search_query = request.args.get("q", "").strip()
    group_filter = request.args.get("group")

    # Get persona groups
    groups_result = current_app.persona_service.get_persona_groups(user_id)
    groups = groups_result.data.get("groups", []) if groups_result.success else []

    # Get personas (with optional search/filter)
    if search_query:
        result = current_app.persona_service.search_personas(user_id, search_query)
    elif group_filter:
        result = current_app.persona_service.get_personas(user_id, group_id=group_filter)
    else:
        result = current_app.persona_service.get_personas(user_id)

    if result.success:
        personas = result.data.get("personas", [])
    else:
        personas = []
        flash(f"Error loading personas: {result.error}", "error")

    # Organize personas by group
    grouped_personas = {}
    ungrouped_personas = []

    if not search_query and not group_filter:
        # Group personas by their group_id
        for persona in personas:
            if persona.group_id:
                if persona.group_id not in grouped_personas:
                    grouped_personas[persona.group_id] = []
                grouped_personas[persona.group_id].append(persona)
            else:
                ungrouped_personas.append(persona)

        # Create a dict with group info
        groups_with_personas = []
        for group in groups:
            if group.id in grouped_personas:
                groups_with_personas.append({
                    'group': group,
                    'personas': grouped_personas[group.id]
                })

    return render_template(
        "personas/library.html",
        personas=personas if (search_query or group_filter) else None,
        groups_with_personas=groups_with_personas if not (search_query or group_filter) else None,
        ungrouped_personas=ungrouped_personas if not (search_query or group_filter) else None,
        groups=groups,
        search_query=search_query,
        selected_group=group_filter
    )


# ============================================================================
# PERSONA CREATION
# ============================================================================

@personas_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new persona with AI enrichment"""
    user_id = session["user"]["id"]

    # Get persona groups for group selector
    groups_result = current_app.persona_service.get_persona_groups(user_id)
    groups = groups_result.data.get("groups", []) if groups_result.success else []

    if request.method == "GET":
        # Check if we have a preset_group_id from "Add Persona" button
        preset_group_id = request.args.get("group_id")
        return render_template("personas/create.html", groups=groups, preset_group_id=preset_group_id)

    # Handle POST - create persona
    description = request.form.get("description", "").strip()

    if not description:
        flash("Please provide a persona description.", "error")
        return render_template("personas/create.html", groups=groups)

    # Generate AI enrichment
    enrichment_result = current_app.gemini_service.generate_persona_enrichment(description)

    if not enrichment_result.success:
        flash(f"AI enrichment failed: {enrichment_result.error}", "error")
        return render_template("personas/create.html", groups=groups, description=description)

    enrichment = enrichment_result.data

    # Check if there's a preset group from query params (for "Add to Group" flow)
    preset_group_id = request.args.get("group_id")

    # Show enrichment for user editing
    return render_template(
        "personas/create.html",
        groups=groups,
        enrichment=enrichment,
        description=description,
        preset_group_id=preset_group_id
    )


@personas_bp.route("/save", methods=["POST"])
@login_required
def save():
    """Save a persona after enrichment (with user edits)"""
    user_id = session["user"]["id"]
    access_token = session["user"].get("access_token")

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

    # Handle group assignment
    suggested_group = request.form.get("suggested_group", "").strip()
    preset_group_id = request.form.get("preset_group_id", "").strip()

    group_id = None

    # Priority: preset_group_id (from "Add to Group" button) > suggested_group (from AI)
    if preset_group_id:
        group_id = preset_group_id
    elif suggested_group:
        # Find or create the group based on suggested name
        groups_result = current_app.persona_service.get_persona_groups(user_id)
        if groups_result.success:
            groups = groups_result.data.get("groups", [])
            # Case-insensitive match
            matching_group = next((g for g in groups if g.name.lower() == suggested_group.lower()), None)

            if matching_group:
                group_id = matching_group.id
            else:
                # Create new group
                new_group_result = current_app.persona_service.create_persona_group(
                    user_id=user_id,
                    name=suggested_group,
                    description=f"Auto-created group for {suggested_group} personas",
                    access_token=access_token
                )
                if new_group_result.success:
                    group_id = new_group_result.data.get("id")

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
        suggested_group=suggested_group or None
    )

    # Save persona
    result = current_app.persona_service.create_persona(user_id, enrichment, group_id, access_token)

    if result.success:
        persona_id = result.data.get("id")
        flash(f"Persona '{name}' created successfully!", "success")
        return redirect(url_for("personas.library"))
    else:
        flash(f"Error saving persona: {result.error}", "error")
        return redirect(url_for("personas.create"))


# ============================================================================
# RELATED PERSONA SUGGESTIONS
# ============================================================================

@personas_bp.route("/<persona_id>/suggestions")
@login_required
def suggestions(persona_id):
    """Show related persona suggestions after creating a persona"""
    user_id = session["user"]["id"]

    # Get the focal persona
    persona_result = current_app.persona_service.get_persona(persona_id)
    if not persona_result.success:
        flash("Persona not found.", "error")
        return redirect(url_for("personas.library"))

    persona_data = persona_result.data
    focal_persona = Persona.from_db_row(persona_data)

    # Get existing personas to avoid duplicates
    existing_result = current_app.persona_service.get_personas(user_id)
    existing_personas = []
    if existing_result.success:
        existing_personas = [Persona.from_db_row(p) for p in existing_result.data.get("personas", [])]

    # Generate suggestions
    suggestions_result = current_app.gemini_service.suggest_related_personas(
        focal_persona,
        existing_personas,
        count=3
    )

    if suggestions_result.success:
        suggestions_list = suggestions_result.data
    else:
        suggestions_list = []
        flash(f"Could not generate suggestions: {suggestions_result.error}", "warning")

    return render_template(
        "personas/suggestions.html",
        persona=persona_data,
        suggestions=suggestions_list
    )


@personas_bp.route("/<persona_id>/accept-suggestion", methods=["POST"])
@login_required
def accept_suggestion(persona_id):
    """Accept a suggested persona and create it with a relationship"""
    user_id = session["user"]["id"]

    # Get suggestion data from form
    name = request.form.get("name")
    role = request.form.get("role")
    company = request.form.get("company")
    relationship_type = request.form.get("relationship_type")
    relationship_label = request.form.get("relationship_label")

    if not name or not role:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    # Create the suggested persona
    enrichment = PersonaEnrichment(
        name=name,
        role=role,
        company=company or None,
        goals=[],
        pains=[],
        tags=["suggested"]
    )

    create_result = current_app.persona_service.create_persona(user_id, enrichment)

    if not create_result.success:
        return jsonify({"success": False, "error": create_result.error}), 500

    new_persona_id = create_result.data.get("id")

    # Create relationship
    rel_result = current_app.persona_service.create_relationship(
        user_id=user_id,
        from_persona_id=persona_id,
        to_persona_id=new_persona_id,
        relationship_type=relationship_type,
        label=relationship_label
    )

    if not rel_result.success:
        # Relationship failed, but persona created - log warning
        flash(f"Persona created but relationship creation failed: {rel_result.error}", "warning")

    return jsonify({"success": True, "persona_id": new_persona_id})


# ============================================================================
# PERSONA EDITING
# ============================================================================

@personas_bp.route("/<persona_id>/edit", methods=["GET", "POST"])
@login_required
def edit(persona_id):
    """Edit an existing persona"""
    user_id = session["user"]["id"]

    # Get persona
    persona_result = current_app.persona_service.get_persona(persona_id)
    if not persona_result.success:
        flash("Persona not found.", "error")
        return redirect(url_for("personas.library"))

    persona = persona_result.data

    # Verify ownership
    if persona.get("user_id") != user_id:
        flash("You don't have permission to edit this persona.", "error")
        return redirect(url_for("personas.library"))

    if request.method == "GET":
        # Get groups for selector
        groups_result = current_app.persona_service.get_persona_groups(user_id)
        groups = groups_result.data.get("groups", []) if groups_result.success else []

        return render_template("personas/edit.html", persona=persona, groups=groups)

    # Handle POST - update persona
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
        "group_id": request.form.get("group_id") or None
    }

    if not updates["name"]:
        flash("Persona name is required.", "error")
        return redirect(url_for("personas.edit", persona_id=persona_id))

    result = current_app.persona_service.update_persona(persona_id, updates)

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
def archive(persona_id):
    """Archive a persona (soft delete)"""
    result = current_app.persona_service.archive_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@personas_bp.route("/<persona_id>/unarchive", methods=["POST"])
@login_required
def unarchive(persona_id):
    """Unarchive a persona"""
    result = current_app.persona_service.unarchive_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@personas_bp.route("/<persona_id>/delete", methods=["POST"])
@login_required
def delete(persona_id):
    """Permanently delete a persona"""
    result = current_app.persona_service.delete_persona(persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


# ============================================================================
# PERSONA GROUPS
# ============================================================================

@personas_bp.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    """Create a new persona group"""
    user_id = session["user"]["id"]
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        return jsonify({"success": False, "error": "Group name is required"}), 400

    result = current_app.persona_service.create_persona_group(user_id, name, description or None)

    if result.success:
        return jsonify({"success": True, "group": result.data})
    else:
        return jsonify({"success": False, "error": result.error}), 500
