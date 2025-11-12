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

    # Get recent conversations for dashboard view
    conversations = []
    if g.conversation_service:
        conv_result = g.conversation_service.get_user_conversations(user_id, limit=5)
        if conv_result.success:
            conversations = conv_result.data.get("conversations", [])

    # Get persona count for showing getting started guide
    persona_count = len(personas)

    # Get the newly created persona ID if present
    created_persona_id = request.args.get("created")

    return render_template(
        "personas/library.html",
        personas=personas,
        search_query=search_query,
        conversations=conversations,
        persona_count=persona_count,
        created_persona_id=created_persona_id
    )


# ============================================================================
# PERSONA CREATION
# ============================================================================

@personas_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new persona with AI enrichment"""
    user_id = session["user"]["id"]

    if request.method == "GET":
        return render_template("personas/create.html")

    # Handle POST - create persona
    description = request.form.get("description", "").strip()

    if not description:
        flash("Please provide a persona description.", "error")
        return render_template("personas/create.html")

    # Generate AI enrichment
    enrichment_result = current_app.gemini_service.generate_persona_enrichment(description)

    if not enrichment_result.success:
        flash(f"AI enrichment failed: {enrichment_result.error}", "error")
        return render_template("personas/create.html", description=description)

    enrichment = enrichment_result.data

    # Show enrichment for user editing
    return render_template(
        "personas/create.html",
        enrichment=enrichment,
        description=description
    )


@personas_bp.route("/save", methods=["POST"])
@login_required
@requires_persona_service
def save():
    """Save a persona after enrichment (with user edits)"""
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
        tags=tags
    )

    # Save persona
    result = g.persona_service.create_persona(user_id, enrichment)

    if result.success:
        persona_id = result.data.get("id")
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
        "notes": request.form.get("notes", "").strip() or None
    }

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
