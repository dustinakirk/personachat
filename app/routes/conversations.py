"""
Conversations Blueprint - Routes for multi-persona chat

Handles conversation creation, messaging, participant management,
and streaming responses from multiple personas.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify, Response, g
from functools import wraps
import json
import re
import logging
import time

from app.models import Persona
from app.decorators import requires_services, requires_conversation_service

conversations_bp = Blueprint("conversations", __name__, url_prefix="/conversations")
logger = logging.getLogger(__name__)


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
# CONVERSATION CREATION
# ============================================================================

@conversations_bp.route("/create", methods=["GET", "POST"])
@login_required
@requires_services
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


@conversations_bp.route("/quick-start/<persona_id>", methods=["GET", "POST"])
@login_required
@requires_services
def quick_start(persona_id):
    """Quick-start a conversation with a single persona (reuses existing if available)"""
    user_id = session["user"]["id"]

    # Verify persona exists and belongs to user
    persona_result = g.persona_service.get_persona(persona_id)
    if not persona_result.success or persona_result.data.user_id != user_id:
        flash("Persona not found.", "error")
        return redirect(url_for("personas.library"))

    # Check for existing conversation with ONLY this persona
    existing_conv_result = g.conversation_service.get_conversation_by_single_participant(user_id, persona_id)

    if existing_conv_result.success and existing_conv_result.data:
        # Reuse existing single-persona conversation
        conversation_id = existing_conv_result.data["id"]
        return redirect(url_for("conversations.chat", conversation_id=conversation_id))

    # No existing single-persona conversation - redirect to new chat with pending persona
    return redirect(url_for("conversations.new_chat", persona_id=persona_id))


# ============================================================================
# CHAT INTERFACE
# ============================================================================

@conversations_bp.route("/")
@login_required
@requires_services
def index():
    """Load most recent conversation directly or show new chat"""
    user_id = session["user"]["id"]

    # Get most recent conversation
    convs_result = g.conversation_service.get_user_conversations(user_id, limit=1)

    if convs_result.success and convs_result.data.get("conversations"):
        # Load most recent conversation directly
        recent_conv = convs_result.data["conversations"][0]
        conversation_id = recent_conv["id"]

        # Get conversation details
        conv_result = g.conversation_service.get_conversation(conversation_id)
        if not conv_result.success:
            return redirect(url_for("conversations.new"))

        conversation = conv_result.data

        # Get participants
        participants_result = g.conversation_service.get_participants(conversation_id)
        participants = participants_result.data.get("participants", []) if participants_result.success else []

        # Get messages
        messages_result = g.conversation_service.get_messages(conversation_id)
        messages = messages_result.data.get("messages", []) if messages_result.success else []

        # Get navigation data
        recent_conversations_result = g.conversation_service.get_user_conversations(user_id, limit=10)
        recent_conversations = recent_conversations_result.data.get("conversations", []) if recent_conversations_result.success else []

        recent_personas_result = g.persona_service.get_personas(user_id)
        recent_personas = recent_personas_result.data.get("personas", [])[:10] if recent_personas_result.success else []

        # Render the most recent conversation directly
        return render_template(
            "conversations/chat.html",
            conversation=conversation,
            pending_persona=None,
            participants=participants,
            messages=messages,
            recent_conversations=recent_conversations,
            recent_personas=recent_personas,
            current_conversation=conversation
        )

    # No conversations - show new chat interface
    return redirect(url_for("conversations.new"))


@conversations_bp.route("/new")
@login_required
@requires_services
def new():
    """Display chat interface for a new conversation without participants"""
    user_id = session["user"]["id"]

    # Get navigation data
    recent_conversations_result = g.conversation_service.get_user_conversations(user_id, limit=10)
    recent_conversations = recent_conversations_result.data.get("conversations", []) if recent_conversations_result.success else []

    recent_personas_result = g.persona_service.get_personas(user_id)
    recent_personas = recent_personas_result.data.get("personas", [])[:10] if recent_personas_result.success else []

    # Render chat with no participants (user will search/select)
    return render_template(
        "conversations/chat.html",
        conversation=None,
        pending_persona=None,
        participants=[],
        messages=[],
        recent_conversations=recent_conversations,
        recent_personas=recent_personas,
        current_conversation=None
    )


@conversations_bp.route("/new_chat")
@login_required
@requires_services
def new_chat():
    """Create a new conversation with a specific persona and display chat interface"""
    user_id = session["user"]["id"]
    persona_id = request.args.get("persona_id")

    if not persona_id:
        return redirect(url_for("conversations.new"))

    # Verify persona exists and belongs to user
    persona_result = g.persona_service.get_persona(persona_id)
    if not persona_result.success or persona_result.data.user_id != user_id:
        flash("Persona not found.", "error")
        return redirect(url_for("conversations.new"))

    # Create conversation immediately with the initial persona
    persona_name = persona_result.data.name
    create_result = g.conversation_service.create_conversation(
        user_id=user_id,
        title=f"Chat with {persona_name}",
        participant_ids=[persona_id]
    )

    if not create_result.success:
        flash(f"Error creating conversation: {create_result.error}", "error")
        return redirect(url_for("conversations.new"))

    # Redirect to the standard chat route with the new conversation ID
    conversation_id = create_result.data.get("id")
    return redirect(url_for("conversations.chat", conversation_id=conversation_id))


@conversations_bp.route("/<conversation_id>")
@login_required
@requires_services
def chat(conversation_id):
    """Display chat interface for an existing conversation"""
    user_id = session["user"]["id"]

    # Verify conversation belongs to user
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        flash("Conversation not found.", "error")
        return redirect(url_for("conversations.index"))

    conversation = conv_result.data

    # Get participants
    participants_result = g.conversation_service.get_participants(conversation_id)
    participants = participants_result.data.get("participants", []) if participants_result.success else []

    # Get messages
    messages_result = g.conversation_service.get_messages(conversation_id)
    messages = messages_result.data.get("messages", []) if messages_result.success else []

    # Get navigation data
    recent_conversations_result = g.conversation_service.get_user_conversations(user_id, limit=10)
    recent_conversations = recent_conversations_result.data.get("conversations", []) if recent_conversations_result.success else []

    recent_personas_result = g.persona_service.get_personas(user_id)
    recent_personas = recent_personas_result.data.get("personas", [])[:10] if recent_personas_result.success else []

    return render_template(
        "conversations/chat.html",
        conversation=conversation,
        pending_persona=None,
        participants=participants,
        messages=messages,
        recent_conversations=recent_conversations,
        recent_personas=recent_personas,
        current_conversation=conversation
    )


@conversations_bp.route("/<conversation_id>/available-personas", methods=["GET"])
@login_required
@requires_services
def get_available_personas(conversation_id):
    """AJAX endpoint to fetch available personas for adding to conversation"""
    user_id = session["user"]["id"]

    # Verify conversation belongs to user
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        return jsonify({"success": False, "error": "Conversation not found"}), 404

    # Get all user's personas
    all_personas_result = g.persona_service.get_personas(user_id)
    if not all_personas_result.success:
        return jsonify({"success": False, "error": "Failed to fetch personas"}), 500

    all_personas = all_personas_result.data.get("personas", [])

    # Get current participants to filter them out
    participants_result = g.conversation_service.get_participants(conversation_id)
    current_participant_ids = []
    if participants_result.success:
        current_participant_ids = [p["id"] for p in participants_result.data.get("participants", [])]

    # Filter out personas that are already participants
    available_personas = [p for p in all_personas if p["id"] not in current_participant_ids]

    return jsonify({
        "success": True,
        "personas": available_personas
    })


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

@conversations_bp.route("/<conversation_id>/send", methods=["POST"])
@login_required
@requires_services
def send_message(conversation_id):
    """Send a user message and return immediately with responder info"""
    user_id = session["user"]["id"]
    message = request.form.get("message", "").strip()

    logger.info(f"Message received | conv_id={conversation_id} user_id={user_id} message_len={len(message)}")

    if not message:
        logger.warning(f"Empty message rejected | conv_id={conversation_id} user_id={user_id}")
        return jsonify({"success": False, "error": "Message is required"}), 400

    if not conversation_id:
        logger.warning(f"Missing conversation_id | user_id={user_id}")
        return jsonify({"success": False, "error": "Conversation ID is required"}), 400

    # Verify conversation ownership
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        logger.warning(f"Conversation not found or unauthorized | conv_id={conversation_id} user_id={user_id}")
        return jsonify({"success": False, "error": "Conversation not found"}), 404

    # Save user message
    start_save = time.time()
    user_msg_result = g.conversation_service.add_user_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=message,
    )
    save_duration = (time.time() - start_save) * 1000

    if not user_msg_result.success:
        logger.error(f"Failed to save user message | conv_id={conversation_id} error={user_msg_result.error} duration_ms={save_duration:.0f}")
        return jsonify({"success": False, "error": user_msg_result.error}), 500

    user_message_id = user_msg_result.data.get("id")
    logger.info(f"User message saved | conv_id={conversation_id} message_id={user_message_id} duration_ms={save_duration:.0f}")

    # Get active participants
    participants_result = g.conversation_service.get_participants(conversation_id)
    if not participants_result.success:
        logger.error(f"Failed to get participants | conv_id={conversation_id} error={participants_result.error}")
        return jsonify({"success": False, "error": "Failed to get participants"}), 500

    participants_data = participants_result.data.get("participants", [])
    active_participants = [p for p in participants_data if p.get("active", True)]
    logger.info(f"Participants retrieved | conv_id={conversation_id} total={len(participants_data)} active={len(active_participants)}")

    if not active_participants:
        logger.warning(f"No active participants | conv_id={conversation_id}")
        return jsonify({"success": True, "message_id": user_message_id, "responders": []})

    # Convert to Persona objects
    participant_personas = [Persona.from_db_row(p) for p in active_participants]

    # OPTIMIZATION 1: Single-participant shortcut - skip all routing
    if len(participant_personas) == 1:
        responders = [participant_personas[0]]
        routing_method = "single_participant"
        logger.info(f"Single participant routing | conv_id={conversation_id} persona={responders[0].name}")
    else:
        # OPTIMIZATION 2: Algorithmic name matching before AI routing
        from app.utils import match_personas_in_message, should_use_ai_routing

        match_result = match_personas_in_message(message, participant_personas)

        # Check routing strategy
        routing_strategy = should_use_ai_routing(match_result, len(participant_personas))

        # Check if this is a generic question - all personas should respond
        if routing_strategy["respond_all"]:
            # Generic question - route to all active personas
            responders = participant_personas
            routing_method = "generic_question:all_personas"
            logger.info(f"Generic question routing | conv_id={conversation_id} all_personas_responding={len(responders)} personas={[p.name for p in responders]}")
        elif match_result["matched_personas"] and not routing_strategy["use_ai_routing"]:
            # High-confidence algorithmic match - use it directly
            responders = match_result["matched_personas"]
            routing_method = f"algorithmic:{match_result['method']}"
            logger.info(f"Algorithmic routing | conv_id={conversation_id} method={match_result['method']} matched={len(responders)} personas={[p.name for p in responders]}")
        else:
            # Use AI routing for ambiguous cases
            logger.info(f"Using AI routing | conv_id={conversation_id} participants={len(participant_personas)}")
            # Get chat history for context
            messages_result = g.conversation_service.get_messages(conversation_id, limit=20)
            chat_history = []
            if messages_result.success:
                for msg in messages_result.data.get("messages", []):
                    chat_history.append({
                        "speaker": msg.get("speaker_name", "Unknown"),
                        "content": msg.get("content", "")
                    })

            start_routing = time.time()
            routing_result = current_app.gemini_service.route_message_to_personas(
                user_message=message,
                participant_personas=participant_personas,
                chat_history=chat_history
            )
            routing_duration = (time.time() - start_routing) * 1000

            if routing_result.success:
                responder_ids = routing_result.data
                responders = [p for p in participant_personas if p.id in responder_ids]
                routing_method = "ai_routing"
                logger.info(f"AI routing completed | conv_id={conversation_id} duration_ms={routing_duration:.0f} selected={len(responders)} personas={[p.name for p in responders]}")
            else:
                # Fallback: first persona responds
                responders = [participant_personas[0]] if participant_personas else []
                routing_method = "fallback"
                logger.warning(f"AI routing failed, using fallback | conv_id={conversation_id} error={routing_result.error} fallback_persona={responders[0].name if responders else 'none'}")

    # Return immediately with responder info
    # The SSE stream endpoint will handle generating the actual responses
    responder_data = [{
        "id": p.id,
        "name": p.name,
        "role": p.role,
        "avatar_emoji": p.avatar_emoji,
        "avatar_color": p.avatar_color
    } for p in responders]

    # Store responder IDs in session for the stream endpoint to use
    session_key = f"responders_{conversation_id}_{user_message_id}"
    session[session_key] = [p.id for p in responders]
    logger.info(f"Responders stored in session | conv_id={conversation_id} message_id={user_message_id} count={len(responders)} session_key={session_key}")

    return jsonify({
        "success": True,
        "message_id": user_message_id,
        "conversation_id": conversation_id,  # Important for pending conversations
        "responders": responder_data,
        "responder_count": len(responders),
        "routing_method": routing_method  # For frontend to conditionally show status
    })


@conversations_bp.route("/<conversation_id>/stream", methods=["GET"])
@login_required
@requires_services
def stream_responses(conversation_id):
    """SSE endpoint that streams persona responses in real-time"""
    import concurrent.futures
    import queue
    import time

    user_id = session["user"]["id"]
    message_id = request.args.get("message_id")

    logger.info(f"SSE stream started | conv_id={conversation_id} message_id={message_id} user_id={user_id}")

    # Verify conversation ownership
    conv_result = g.conversation_service.get_conversation(conversation_id)
    if not conv_result.success or conv_result.data.get("user_id") != user_id:
        logger.warning(f"SSE stream unauthorized | conv_id={conversation_id} user_id={user_id}")
        return jsonify({"success": False, "error": "Conversation not found"}), 404

    # Get conversation context if available
    conversation_context = conv_result.data.get("context")

    # Get the latest user message (order descending to get most recent first)
    messages_result = g.conversation_service.get_messages(conversation_id, limit=1, order_desc=True)
    if not messages_result.success:
        logger.error(f"Failed to get messages | conv_id={conversation_id} error={messages_result.error}")
        return jsonify({"success": False, "error": "Failed to get messages"}), 500

    messages = messages_result.data.get("messages", [])
    if not messages or messages[0].get("persona_id"):
        logger.warning(f"No user message found | conv_id={conversation_id}")
        return jsonify({"success": False, "error": "No user message found"}), 400

    latest_message = messages[0]["content"]
    logger.debug(f"Latest message retrieved | conv_id={conversation_id} message_len={len(latest_message)}")

    # Get active participants
    participants_result = g.conversation_service.get_participants(conversation_id)
    if not participants_result.success:
        logger.error(f"Failed to get participants for stream | conv_id={conversation_id} error={participants_result.error}")
        return jsonify({"success": False, "error": "Failed to get participants"}), 500

    participants_data = participants_result.data.get("participants", [])
    active_participants = [p for p in participants_data if p.get("active", True)]
    logger.info(f"Participants for stream | conv_id={conversation_id} total={len(participants_data)} active={len(active_participants)}")

    if not active_participants:
        logger.warning(f"No active participants for stream | conv_id={conversation_id}")
        # Send completion event and close
        def generate():
            yield f"data: {json.dumps({'type': 'complete', 'message': 'No active participants'})}\n\n"
        return Response(generate(), mimetype="text/event-stream")

    participant_personas = [Persona.from_db_row(p) for p in active_participants]

    # Get responder IDs from session (already determined in /send endpoint)
    session_key = f"responders_{conversation_id}_{message_id}"
    responder_ids = session.get(session_key, [])
    logger.debug(f"Session lookup | conv_id={conversation_id} session_key={session_key} found_ids={len(responder_ids)}")

    # Clean up session key after retrieval
    if session_key in session:
        session.pop(session_key)

    # Get responder personas by ID
    responders = [p for p in participant_personas if p.id in responder_ids]

    # Fallback if no responders found in session (shouldn't happen in normal flow)
    if not responders:
        logger.warning(f"No responders in session, using fallback | conv_id={conversation_id} session_key={session_key}")
        responders = [participant_personas[0]] if participant_personas else []

    logger.info(f"Responders selected for stream | conv_id={conversation_id} count={len(responders)} personas={[p.name for p in responders]}")

    # Get chat history
    all_messages_result = g.conversation_service.get_messages(conversation_id, limit=20)
    chat_history = []
    if all_messages_result.success:
        for msg in all_messages_result.data.get("messages", []):
            chat_history.append({
                "speaker": msg.get("speaker_name", "Unknown"),
                "content": msg.get("content", "")
            })

    other_personas = [p for p in participant_personas if p not in responders]

    # Capture service references BEFORE creating generator (to avoid application context issues)
    gemini_service = current_app.gemini_service
    persona_service = g.persona_service
    conversation_service = g.conversation_service

    def generate():
        """Generator function that yields SSE events"""
        # Send initial event with responders
        yield f"data: {json.dumps({'type': 'responders', 'responders': [{'id': p.id, 'name': p.name} for p in responders]})}\n\n"

        # Create a queue to collect chunks from all personas
        event_queue = queue.Queue()

        def stream_persona_response(persona, gemini_svc, persona_svc, conversation_svc, target_queue=None):
            """Stream a single persona's response"""
            queue_to_use = target_queue if target_queue is not None else event_queue
            persona_start_time = time.time()

            try:
                logger.info(f"Persona response started | conv_id={conversation_id} persona_id={persona.id} persona_name={persona.name}")

                # Signal typing start
                queue_to_use.put({
                    'type': 'typing_start',
                    'persona_id': persona.id,
                    'persona_name': persona.name
                })

                # Get relationships
                relationships_dict = {}
                if persona_svc:
                    rels_result = persona_svc.get_relationships(persona.id)
                    if rels_result.success:
                        rel_count = len(rels_result.data.get("outgoing", []))
                        for rel in rels_result.data.get("outgoing", []):
                            if rel.to_persona_id in [p.id for p in other_personas]:
                                relationships_dict[rel.to_persona_id] = {
                                    "relationship_type": rel.relationship_type,
                                    "shared_context": rel.shared_context,
                                    "interaction_style": rel.interaction_style
                                }
                        logger.debug(f"Relationships loaded | conv_id={conversation_id} persona_id={persona.id} total={rel_count} relevant={len(relationships_dict)}")
                    else:
                        logger.warning(f"Failed to load relationships | conv_id={conversation_id} persona_id={persona.id} error={rels_result.error}")

                # Generate streaming response
                logger.info(f"Gemini API streaming call START | conv_id={conversation_id} persona_id={persona.id} persona_name={persona.name}")
                api_start_time = time.time()

                stream_result = gemini_svc.generate_persona_response_streaming(
                    persona=persona,
                    user_message=latest_message,
                    chat_history=chat_history,
                    other_personas=other_personas,
                    relationships=relationships_dict if relationships_dict else None,
                    conversation_context=conversation_context
                )

                if stream_result.success:
                    full_response = ""
                    chunk_count = 0
                    for chunk in stream_result.data:
                        full_response += chunk
                        chunk_count += 1
                        queue_to_use.put({
                            'type': 'chunk',
                            'persona_id': persona.id,
                            'persona_name': persona.name,
                            'chunk': chunk
                        })

                    api_duration = (time.time() - api_start_time) * 1000
                    logger.info(f"Gemini API streaming COMPLETE | conv_id={conversation_id} persona_id={persona.id} chunks={chunk_count} response_len={len(full_response)} api_duration_ms={api_duration:.0f}")

                    # Save complete response to database
                    logger.debug(f"DB save START | conv_id={conversation_id} persona_id={persona.id} response_len={len(full_response)}")
                    db_save_start = time.time()

                    save_result = conversation_svc.add_persona_message(
                        conversation_id=conversation_id,
                        persona_id=persona.id,
                        content=full_response
                    )

                    db_save_duration = (time.time() - db_save_start) * 1000

                    if save_result.success:
                        logger.info(f"DB save COMPLETE | conv_id={conversation_id} persona_id={persona.id} duration_ms={db_save_duration:.0f}")
                    else:
                        logger.error(f"DB save FAILED | conv_id={conversation_id} persona_id={persona.id} error={save_result.error} duration_ms={db_save_duration:.0f}")

                    # Signal completion
                    total_duration = (time.time() - persona_start_time) * 1000
                    logger.info(f"Persona response COMPLETE | conv_id={conversation_id} persona_id={persona.id} persona_name={persona.name} total_duration_ms={total_duration:.0f}")

                    queue_to_use.put({
                        'type': 'persona_complete',
                        'persona_id': persona.id,
                        'persona_name': persona.name
                    })
                else:
                    api_duration = (time.time() - api_start_time) * 1000
                    logger.error(f"Gemini API streaming FAILED | conv_id={conversation_id} persona_id={persona.id} error={stream_result.error} api_duration_ms={api_duration:.0f}")

                    queue_to_use.put({
                        'type': 'error',
                        'persona_id': persona.id,
                        'error': stream_result.error
                    })

            except Exception as e:
                total_duration = (time.time() - persona_start_time) * 1000
                logger.error(f"Persona response EXCEPTION | conv_id={conversation_id} persona_id={persona.id} exception_type={type(e).__name__} error={str(e)} duration_ms={total_duration:.0f}", exc_info=True)

                queue_to_use.put({
                    'type': 'error',
                    'persona_id': persona.id,
                    'error': str(e)
                })

        # Start all persona response streams in parallel
        logger.info(f"Thread pool START | conv_id={conversation_id} thread_count={len(responders)}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(responders)) as executor:
            futures = [executor.submit(stream_persona_response, persona, gemini_service, persona_service, conversation_service) for persona in responders]

            # Track completion
            completed_count = 0
            timeout = 300  # 5 minute timeout
            start_time = time.time()
            failed_personas = set()  # Track which personas failed
            queue_timeout_count = 0

            # Yield events as they arrive
            while completed_count < len(responders):
                try:
                    elapsed = time.time() - start_time

                    # Check timeout
                    if elapsed > timeout:
                        logger.error(f"Overall timeout reached | conv_id={conversation_id} elapsed_sec={elapsed:.1f} completed={completed_count}/{len(responders)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout waiting for responses'})}\n\n"
                        break

                    # Get event with timeout
                    event = event_queue.get(timeout=0.5)

                    if event['type'] == 'persona_complete':
                        completed_count += 1
                        logger.debug(f"Event: persona_complete | conv_id={conversation_id} persona_id={event.get('persona_id')} completed={completed_count}/{len(responders)}")
                    elif event['type'] == 'error':
                        # Track failed persona for potential retry and count as "completed" attempt
                        persona_id = event.get('persona_id')
                        if persona_id:
                            failed_personas.add(persona_id)
                        completed_count += 1  # Count errors as completed attempts to exit loop
                        logger.warning(f"Event: error | conv_id={conversation_id} persona_id={persona_id} error={event.get('error')} completed={completed_count}/{len(responders)}")

                    yield f"data: {json.dumps(event)}\n\n"

                except queue.Empty:
                    queue_timeout_count += 1
                    if queue_timeout_count % 10 == 0:  # Log every 5 seconds (10 * 0.5s)
                        logger.debug(f"Queue timeout iteration | conv_id={conversation_id} count={queue_timeout_count} elapsed_sec={time.time() - start_time:.1f} completed={completed_count}/{len(responders)}")
                    continue

            # Wait for all threads to complete
            logger.debug(f"Waiting for thread pool to complete | conv_id={conversation_id}")
            concurrent.futures.wait(futures, timeout=5)
            logger.info(f"Thread pool COMPLETE | conv_id={conversation_id} completed={completed_count}/{len(responders)} failed={len(failed_personas)}")

        # Retry failed personas once
        if failed_personas:
            logger.warning(f"Retry initiated | conv_id={conversation_id} failed_count={len(failed_personas)} personas={list(failed_personas)}")
            yield f"data: {json.dumps({'type': 'info', 'message': f'Retrying {len(failed_personas)} failed persona(s)...'})}\n\n"

            retry_responders = [p for p in responders if p.id in failed_personas]
            retry_queue = queue.Queue()

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(retry_responders)) as retry_executor:
                retry_futures = [retry_executor.submit(stream_persona_response, persona, gemini_service, persona_service, conversation_service, retry_queue) for persona in retry_responders]

                retry_completed = 0
                retry_timeout = 60  # 1 minute for retries
                retry_start = time.time()

                while retry_completed < len(retry_responders):
                    try:
                        retry_elapsed = time.time() - retry_start
                        if retry_elapsed > retry_timeout:
                            logger.error(f"Retry timeout | conv_id={conversation_id} elapsed_sec={retry_elapsed:.1f} completed={retry_completed}/{len(retry_responders)}")
                            yield f"data: {json.dumps({'type': 'error', 'message': 'Retry timeout'})}\n\n"
                            break

                        event = retry_queue.get(timeout=0.5)

                        if event['type'] == 'persona_complete':
                            retry_completed += 1
                            logger.info(f"Retry success | conv_id={conversation_id} persona_id={event.get('persona_id')} completed={retry_completed}/{len(retry_responders)}")

                        yield f"data: {json.dumps(event)}\n\n"

                    except queue.Empty:
                        continue

                concurrent.futures.wait(retry_futures, timeout=5)
                logger.info(f"Retry COMPLETE | conv_id={conversation_id} successful={retry_completed}/{len(retry_responders)}")

        # Send final completion event
        total_elapsed = time.time() - start_time
        logger.info(f"SSE stream COMPLETE | conv_id={conversation_id} total_duration_sec={total_elapsed:.1f} responders={len(responders)} failed={len(failed_personas)}")
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


# ============================================================================
# PARTICIPANT MANAGEMENT
# ============================================================================

@conversations_bp.route("/<conversation_id>/participants/add", methods=["POST"])
@login_required
@requires_conversation_service
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
@requires_conversation_service
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
@requires_conversation_service
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
@requires_conversation_service
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
@requires_conversation_service
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


@conversations_bp.route("/<conversation_id>/context", methods=["POST"])
@login_required
@requires_conversation_service
def update_context(conversation_id):
    """Update conversation context - background information that informs persona responses"""
    context = request.form.get("context", "").strip()

    # Allow empty context (user may want to clear it)
    result = g.conversation_service.update_conversation_context(conversation_id, context)

    if result.success:
        return jsonify({"success": True, "context": context})
    else:
        return jsonify({"success": False, "error": result.error}), 500
