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

    # If logged in, redirect to personas library (new home page)
    if user:
        return redirect(url_for("personas.library"))

    # If not logged in, show landing page
    return render_template("index.html", user=user)


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"):
        return redirect(url_for("main.index"))

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
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        supabase = current_app.supabase_service
        if not supabase.is_configured:
            flash("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.", "error")
        else:
            result = supabase.login_user(email, password)
            if result.success and result.data:
                session.permanent = True
                session["user"] = {
                    "email": result.data.get("email"),
                    "id": result.data.get("id"),
                    "access_token": result.data.get("access_token"),
                    "refresh_token": result.data.get("refresh_token")
                }
                flash("Welcome back!", "success")
                return redirect(url_for("main.index"))
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
