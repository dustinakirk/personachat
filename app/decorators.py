"""Decorators for route protection and validation"""
from functools import wraps
from flask import g, session, redirect, url_for, flash


def requires_services(f):
    """
    Decorator to ensure persona_service and conversation_service are available.
    If services are not initialized, clears the session and redirects to login.
    This prevents AttributeError when services fail to initialize.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'persona_service') or g.persona_service is None:
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("main.login"))
        if not hasattr(g, 'conversation_service') or g.conversation_service is None:
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function


def requires_persona_service(f):
    """
    Decorator to ensure persona_service is available.
    Use for routes that only need persona_service (not conversation_service).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'persona_service') or g.persona_service is None:
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function


def requires_conversation_service(f):
    """
    Decorator to ensure conversation_service is available.
    Use for routes that only need conversation_service (not persona_service).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'conversation_service') or g.conversation_service is None:
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated_function
