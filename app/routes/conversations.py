"""
Conversations Blueprint - Routes for multi-persona chat

Handles conversation creation, messaging, participant management,
and streaming responses from multiple personas.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify, Response, g
from functools import wraps
import json
import re

from app.models import Persona

conversations_bp = Blueprint("conversations", __name__, url_prefix="/conversations")


def login_required(f):
    """Decorator to require login for conversation routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access conversations.", "error")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# CONVERSATION LISTING & MANAGEMENT
# ============================================================================

@conversations_bp.route("/")
@login_required
def list_conversations():
    """List recent conversations"""
    user_id = session["user"]["id"]

    result = g.conversation_service.get_user_conversations(user_id, limit=20)

    if result.success:
        conversations = result.data.get("conversations", [])
    else:
        conversations = []
        flash(f"Error loading conversations: {result.error}", "error")

    return render_template("conversations/list.html", conversations=conversations)


# ============================================================================
# CONVERSATION CREATION
# ============================================================================

@conversations_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new conversation with selected personas"""
    user_id = session["user"]["id"]

    if request.method == "GET":
        # Get available personas for selection
        personas_result = g.persona_service.get_personas(user_id)
        personas = personas_result.data.get("personas", []) if personas_result.success else []

        return render_template("conversations/create.html", personas=personas)

    # Handle POST - create conversation
    participant_ids = request.form.getlist("participant_ids")

    if not participant_ids or len(participant_ids) == 0:
        flash("Please select at least one persona to start a conversation.", "error")
        return redirect(url_for("conversations.create"))

    if len(participant_ids) > 5:
        flash("Please select no more than 5 personas.", "error")
        return redirect(url_for("conversations.create"))

    # Create conversation
    result = g.conversation_service.create_conversation(
        user_id=user_id,
        title="New Conversation",
        participant_ids=participant_ids,
    )

    if result.success:
        conversation_id = result.data.get("id")
        return redirect(url_for("conversations.chat", conversation_id=conversation_id))
    else:
        flash(f"Error creating conversation: {result.error}", "error")
        return redirect(url_for("conversations.create"))


# ============================================================================
# CHAT INTERFACE
# ============================================================================

@conversations_bp.route("/<conversation_id>")
@login_required
def chat(conversation_id):
    """Display chat interface for a conversation"""
    user_id = session["user"]["id"]

    # Verify conversation belongs to user
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        flash("Conversation not found.", "error")
        return redirect(url_for("conversations.list_conversations"))

    conversation = conv_result.data

    # Get participants
    participants_result = g.conversation_service.get_participants(conversation_id)
    participants = participants_result.data.get("participants", []) if participants_result.success else []

    # Get messages
    messages_result = g.conversation_service.get_messages(conversation_id)
    messages = messages_result.data.get("messages", []) if messages_result.success else []

    # Get all user's personas for adding more participants
    all_personas_result = g.persona_service.get_personas(user_id)
    all_personas = all_personas_result.data.get("personas", []) if all_personas_result.success else []

    return render_template(
        "conversations/chat.html",
        conversation=conversation,
        participants=participants,
        messages=messages,
        all_personas=all_personas
    )


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

@conversations_bp.route("/<conversation_id>/send", methods=["POST"])
@login_required
def send_message(conversation_id):
    """Send a user message and get persona responses"""
    user_id = session["user"]["id"]
    message = request.form.get("message", "").strip()

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    # Verify conversation ownership
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        return jsonify({"success": False, "error": "Conversation not found"}), 404

    # Save user message
    user_msg_result = g.conversation_service.add_user_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=message,
    )

    if not user_msg_result.success:
        return jsonify({"success": False, "error": user_msg_result.error}), 500

    # Get active participants
    participants_result = g.conversation_service.get_participants(conversation_id)
    if not participants_result.success:
        return jsonify({"success": False, "error": "Failed to get participants"}), 500

    participants_data = participants_result.data.get("participants", [])
    active_participants = [p for p in participants_data if p.get("active", True)]

    if not active_participants:
        return jsonify({"success": True, "responses": []})

    # Convert to Persona objects
    participant_personas = [Persona.from_db_row(p) for p in active_participants]

    # Check for @mentions to determine directed messages
    mentioned_persona = None
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, message)

    if mentions:
        # Find persona by name (case-insensitive)
        mention_name = mentions[0].lower()
        for p in participant_personas:
            if p.name.lower().startswith(mention_name):
                mentioned_persona = p
                break

    # Get chat history for context
    messages_result = g.conversation_service.get_messages(conversation_id, limit=20)
    chat_history = []
    if messages_result.success:
        for msg in messages_result.data.get("messages", []):
            chat_history.append({
                "speaker": msg.get("speaker_name", "Unknown"),
                "content": msg.get("content", "")
            })

    # Route message to personas
    responders = []

    if mentioned_persona:
        # Directed message - only mentioned persona responds
        responders = [mentioned_persona]
    else:
        # Use AI routing to determine who should respond
        routing_result = current_app.gemini_service.route_message_to_personas(
            user_message=message,
            participant_personas=participant_personas,
            chat_history=chat_history,
            max_responders=3
        )

        if routing_result.success:
            responder_ids = routing_result.data
            responders = [p for p in participant_personas if p.id in responder_ids]
        else:
            # Fallback: first persona responds
            responders = [participant_personas[0]] if participant_personas else []

    # Generate responses from selected personas
    responses = []
    other_personas = [p for p in participant_personas if p not in responders]

    for persona in responders:
        response_result = current_app.gemini_service.generate_persona_response(
            persona=persona,
            user_message=message,
            chat_history=chat_history,
            other_personas=other_personas
        )

        if response_result.success:
            response_text = response_result.data

            # Save persona response
            g.conversation_service.add_persona_message(
                conversation_id=conversation_id,
                persona_id=persona.id,
                content=response_text,
                    )

            responses.append({
                "persona_id": persona.id,
                "persona_name": persona.name,
                "persona_role": persona.role,
                "content": response_text
            })

    return jsonify({"success": True, "responses": responses})


# ============================================================================
# PARTICIPANT MANAGEMENT
# ============================================================================

@conversations_bp.route("/<conversation_id>/participants/add", methods=["POST"])
@login_required
def add_participant(conversation_id):
    """Add a persona to the conversation"""
    persona_id = request.form.get("persona_id")

    if not persona_id:
        return jsonify({"success": False, "error": "Persona ID is required"}), 400

    result = g.conversation_service.add_participant(conversation_id, persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@conversations_bp.route("/<conversation_id>/participants/remove", methods=["POST"])
@login_required
def remove_participant(conversation_id):
    """Remove a persona from the conversation"""
    persona_id = request.form.get("persona_id")

    if not persona_id:
        return jsonify({"success": False, "error": "Persona ID is required"}), 400

    result = g.conversation_service.remove_participant(conversation_id, persona_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@conversations_bp.route("/<conversation_id>/participants/toggle", methods=["POST"])
@login_required
def toggle_participant(conversation_id):
    """Toggle a participant's active status (mute/unmute)"""
    persona_id = request.form.get("persona_id")
    active = request.form.get("active", "true").lower() == "true"

    if not persona_id:
        return jsonify({"success": False, "error": "Persona ID is required"}), 400

    result = g.conversation_service.toggle_participant(conversation_id, persona_id, active)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


# ============================================================================
# CONVERSATION UTILITIES
# ============================================================================

@conversations_bp.route("/<conversation_id>/delete", methods=["POST"])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation"""
    user_id = session["user"]["id"]

    # Verify ownership
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        return jsonify({"success": False, "error": "Conversation not found"}), 404

    result = g.conversation_service.delete_conversation(conversation_id)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500


@conversations_bp.route("/<conversation_id>/title", methods=["POST"])
@login_required
def update_title(conversation_id):
    """Update conversation title"""
    title = request.form.get("title", "").strip()

    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400

    result = g.conversation_service.update_conversation_title(conversation_id, title)

    if result.success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result.error}), 500
