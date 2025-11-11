from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
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
    return render_template("index.html", user=session.get("user"))


@main_bp.route("/application", methods=["GET", "POST"])
@login_required
def application():
    prompt = ""
    gemini_response = None
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

        try:
            gemini_response = current_app.gemini_service.generate_response(prompt)

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
        except Exception as exc:  # pylint: disable=broad-except
            flash(str(exc), "error")

    return render_template(
        "application.html",
        user=user,
        prompt=prompt,
        gemini_response=gemini_response,
        gemini_ready=current_app.gemini_service.is_configured,
        conversations=conversations,
    )


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
                result = supabase.register_user(email, password)
                if result.success:
                    flash("Account created. Please log in.", "success")
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
