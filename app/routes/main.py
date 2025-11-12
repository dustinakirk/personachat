from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

main_bp = Blueprint("main", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("main.login"))
        return view_func(*args, **kwargs)

    return wrapped_view


@main_bp.route("/")
def index():
    user = session.get("user")

    # If logged in, show dashboard
    if user:
        user_id = user.get("id")

        # Get recent conversations
        conversations = []
        if current_app.conversation_service:
            conv_result = current_app.conversation_service.get_user_conversations(user_id, limit=5)
            if conv_result.success:
                conversations = conv_result.data.get("conversations", [])

        # Get persona count
        persona_count = 0
        if current_app.persona_service:
            personas_result = current_app.persona_service.get_personas(user_id)
            if personas_result.success:
                persona_count = len(personas_result.data.get("personas", []))

        return render_template(
            "dashboard.html",
            user=user,
            conversations=conversations,
            persona_count=persona_count
        )

    # If not logged in, show landing page
    return render_template("index.html", user=user)


@main_bp.route("/application", methods=["GET", "POST"])
@login_required
def application():
    prompt = ""
    gemini_response = None
    selected_model = None
    user = session.get("user")
    user_id = user.get("id") if user else None

    # Load conversation history
    conversations = []
    if user_id:
        history_result = current_app.supabase_service.get_user_conversations(user_id, limit=20)
        if history_result.success and history_result.data:
            conversations = history_result.data.get("conversations", [])

    if request.method == "POST":
        prompt = request.form.get("prompt", "")
        selected_model = request.form.get("model", None)

        # Generate response using new GeminiResult pattern
        result = current_app.gemini_service.generate_response(prompt, model=selected_model)

        if result.success:
            gemini_response = result.data

            # Save conversation to database
            if user_id and gemini_response:
                save_result = current_app.supabase_service.save_conversation(
                    user_id, prompt, gemini_response
                )
                if save_result.success:
                    # Reload conversations to include the new one
                    history_result = current_app.supabase_service.get_user_conversations(user_id, limit=20)
                    if history_result.success and history_result.data:
                        conversations = history_result.data.get("conversations", [])
                else:
                    flash(f"Conversation saved to session only: {save_result.error}", "warning")
        else:
            flash(result.error, "error")

    return render_template(
        "application.html",
        user=user,
        prompt=prompt,
        gemini_response=gemini_response,
        gemini_ready=current_app.gemini_service.is_configured,
        available_models=current_app.gemini_service.available_models,
        default_model=current_app.gemini_service.default_model,
        conversations=conversations,
    )


@main_bp.route("/stream", methods=["POST"])
@login_required
def stream():
    """Server-Sent Events endpoint for streaming Gemini responses."""
    prompt = request.json.get("prompt", "")
    selected_model = request.json.get("model", None)
    user = session.get("user")
    user_id = user.get("id") if user else None

    if not prompt.strip():
        return Response("data: {\"error\": \"Empty prompt\"}\n\n", mimetype="text/event-stream")

    def generate():
        """Generator function for SSE streaming."""
        full_response = ""

        try:
            for chunk in current_app.gemini_service.generate_streaming_response(prompt, model=selected_model):
                full_response += chunk
                # Send chunk in SSE format
                yield f"data: {chunk}\n\n"

            # After streaming completes, save to database
            if user_id and full_response:
                save_result = current_app.supabase_service.save_conversation(
                    user_id, prompt, full_response
                )
                if not save_result.success:
                    yield f"data: [ERROR: Failed to save conversation]\n\n"

            # Send completion signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"

    return Response(generate(), mimetype="text/event-stream")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"):
        return redirect(url_for("main.application"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            supabase = current_app.supabase_service
            if not supabase.is_configured:
                flash("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.", "error")
            else:
                # Build redirect URL for email confirmation
                app_url = current_app.config.get("APP_URL", "http://127.0.0.1:8000")
                redirect_url = f"{app_url}/auth/callback"

                result = supabase.register_user(email, password, redirect_to=redirect_url)
                if result.success:
                    flash("Account created. Please check your email to confirm your account.", "success")
                    return redirect(url_for("main.login"))
                flash(result.error or "Unable to register.", "error")

    return render_template("auth/register.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("main.application"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        supabase = current_app.supabase_service
        if not supabase.is_configured:
            flash("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.", "error")
        else:
            result = supabase.login_user(email, password)
            if result.success and result.data:
                session["user"] = {"email": result.data.get("email"), "id": result.data.get("id")}
                flash("Welcome back!", "success")
                return redirect(url_for("main.application"))
            flash(result.error or "Invalid credentials.", "error")

    return render_template("auth/login.html")


@main_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/auth/callback")
def auth_callback():
    """Handle email confirmation callback from Supabase."""
    # Supabase sends the access token and refresh token as URL fragments
    # which are handled client-side. We just need to provide a landing page
    # that shows the user they've been confirmed and redirects to login.
    flash("Email confirmed successfully! Please log in to continue.", "success")
    return redirect(url_for("main.login"))
