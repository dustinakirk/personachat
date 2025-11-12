"""
Network Blueprint - Routes for network visualization

Handles network graph data, relationship management, and expansion.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from functools import wraps

network_bp = Blueprint("network", __name__, url_prefix="/network")


def login_required(f):
    """Decorator to require login for network routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access the network.", "error")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# NETWORK VISUALIZATION
# ============================================================================

@network_bp.route("/")
@login_required
def view():
    """Display network visualization"""
    persona_id = request.args.get("persona_id")  # Optional focal persona
    return render_template("network.html", focal_persona_id=persona_id)


@network_bp.route("/data")
@login_required
def get_network_data():
    """API endpoint to get network graph data as JSON"""
    user_id = session["user"]["id"]
    focal_persona_id = request.args.get("persona_id")  # Optional

    result = current_app.persona_service.get_network_data(user_id, focal_persona_id)

    if result.success:
        personas = result.data.get("personas", [])
        relationships = result.data.get("relationships", [])

        # Transform to Cytoscape.js format
        nodes = []
        for p in personas:
            nodes.append({
                "data": {
                    "id": p["id"],
                    "label": p["name"],
                    "role": p.get("role", ""),
                    "company": p.get("company", ""),
                    "group_id": p.get("group_id")
                }
            })

        edges = []
        for r in relationships:
            edges.append({
                "data": {
                    "id": r["id"],
                    "source": r["from_persona_id"],
                    "target": r["to_persona_id"],
                    "label": r.get("label") or r.get("relationship_type", ""),
                    "relationship_type": r.get("relationship_type", "peer")
                }
            })

        return jsonify({
            "success": True,
            "elements": {
                "nodes": nodes,
                "edges": edges
            }
        })
    else:
        return jsonify({"success": False, "error": result.error}), 500


# ============================================================================
# RELATIONSHIP MANAGEMENT
# ============================================================================

@network_bp.route("/relationships/create", methods=["POST"])
@login_required
def create_relationship():
    """Create a new relationship between two personas"""
    user_id = session["user"]["id"]

    data = request.get_json()
    from_persona_id = data.get("from_persona_id")
    to_persona_id = data.get("to_persona_id")
    relationship_type = data.get("relationship_type", "peer")
    label = data.get("label")

    if not from_persona_id or not to_persona_id:
        return jsonify({"success": False, "error": "Missing persona IDs"}), 400

    result = current_app.persona_service.create_relationship(
        user_id=user_id,
        from_persona_id=from_persona_id,
        to_persona_id=to_persona_id,
        relationship_type=relationship_type,
        label=label
    )

    if result.success:
        return jsonify({"success": True, "relationship": result.data})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@network_bp.route("/relationships/<relationship_id>/update", methods=["POST"])
@login_required
def update_relationship(relationship_id):
    """Update a relationship (change label or type)"""
    data = request.get_json()
    updates = {}

    if "label" in data:
        updates["label"] = data["label"]
    if "relationship_type" in data:
        updates["relationship_type"] = data["relationship_type"]

    if not updates:
        return jsonify({"success": False, "error": "No updates provided"}), 400

    result = current_app.persona_service.update_relationship(relationship_id, updates)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@network_bp.route("/relationships/<relationship_id>/delete", methods=["POST"])
@login_required
def delete_relationship(relationship_id):
    """Delete a relationship"""
    result = current_app.persona_service.delete_relationship(relationship_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


# ============================================================================
# NETWORK EXPANSION (Suggestions)
# ============================================================================

@network_bp.route("/expand/<persona_id>")
@login_required
def expand_suggestions(persona_id):
    """Get expansion suggestions for a persona (AJAX endpoint)"""
    user_id = session["user"]["id"]

    # Get the focal persona
    persona_result = current_app.persona_service.get_persona(persona_id)
    if not persona_result.success:
        return jsonify({"success": False, "error": "Persona not found"}), 404

    from app.models import Persona
    persona_data = persona_result.data
    focal_persona = Persona.from_db_row(persona_data)

    # Get existing personas
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
        suggestions_list = [s.to_dict() for s in suggestions_result.data]
        return jsonify({"success": True, "suggestions": suggestions_list})
    else:
        return jsonify({"success": False, "error": suggestions_result.error}), 500
