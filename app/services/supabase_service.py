from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from supabase import Client, create_client, ClientOptions
from supabase_auth import SyncMemoryStorage

logger = logging.getLogger(__name__)


@dataclass
class SupabaseResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Any] = None


class SupabaseService:
    """Lightweight wrapper around the Supabase Python client."""

    def __init__(self, url: str, key: str) -> None:
        self._url = url
        self._key = key
        self._client: Optional[Client] = None

        if url and key:
            self._client = create_client(url, key)

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def get_authenticated_client(self, access_token: str) -> Optional[Client]:
        """
        Create a Supabase client authenticated with a user's JWT token.
        This allows RLS policies to work correctly using auth.uid().
        """
        if not self._url or not self._key:
            logger.error("Supabase configuration missing; cannot create authenticated client")
            logger.error(f"URL present: {bool(self._url)}, Key present: {bool(self._key)}")
            return None

        if not access_token:
            logger.error("Access token missing while requesting authenticated Supabase client")
            return None

        # Log token format for debugging (first and last 10 chars only for security)
        token_preview = f"{access_token[:10]}...{access_token[-10:]}" if len(access_token) > 20 else "[short token]"
        logger.info(f"Creating authenticated client with token: {token_preview}")

        try:
            # Create client with user's access token in Authorization header
            # Do NOT set apikey in headers - let create_client() handle it
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            options = ClientOptions(
                headers=headers,
                storage=SyncMemoryStorage(),
                auto_refresh_token=True,   # Enable automatic token refresh
                persist_session=False       # Don't persist session state
            )
            client = create_client(self._url, self._key, options=options)

            # Set auth token on postgrest client for RLS policies
            client.postgrest.auth(access_token)

            logger.info("Successfully created authenticated Supabase client")
            return client
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Failed to create authenticated Supabase client. Exception type: {type(exc).__name__}")
            logger.error(f"Exception details: {str(exc)}")
            logger.exception("Full traceback:")
            return None

    def register_user(self, email: str, password: str, redirect_to: str = None) -> SupabaseResult:
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            options = {}
            if redirect_to:
                options["email_redirect_to"] = redirect_to

            response = self._client.auth.sign_up({
                "email": email,
                "password": password,
                "options": options
            })
            if response.user:
                return SupabaseResult(True, data={"id": response.user.id, "email": response.user.email})
            return SupabaseResult(False, error="Signup failed without additional details.")
        except Exception as exc:  # pylint: disable=broad-except
            return SupabaseResult(False, error=str(exc))

    def login_user(self, email: str, password: str) -> SupabaseResult:
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            response = self._client.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                return SupabaseResult(
                    True,
                    data={
                        "id": response.user.id,
                        "email": response.user.email,
                        "access_token": response.session and response.session.access_token,
                        "refresh_token": response.session and response.session.refresh_token,
                    },
                )
            return SupabaseResult(False, error="Invalid credentials.")
        except Exception as exc:  # pylint: disable=broad-except
            return SupabaseResult(False, error=str(exc))

    def refresh_session(self, refresh_token: str) -> SupabaseResult:
        """
        Refresh an expired access token using the refresh token.
        Returns new access_token and refresh_token.
        """
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            response = self._client.auth.refresh_session(refresh_token)
            if response.session:
                return SupabaseResult(
                    True,
                    data={
                        "access_token": response.session.access_token,
                        "refresh_token": response.session.refresh_token,
                        "user": {
                            "id": response.user.id,
                            "email": response.user.email,
                        } if response.user else None,
                    },
                )
            return SupabaseResult(False, error="Failed to refresh session.")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Failed to refresh session: {str(exc)}")
            return SupabaseResult(False, error=str(exc))

    def create_user_profile(self, user_id: str, display_name: str = "") -> SupabaseResult:
        """Create a user profile with optional display name."""
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            data = {"user_id": user_id, "display_name": display_name}
            result = self._client.table("user_profiles").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:  # pylint: disable=broad-except
            return SupabaseResult(False, error=str(exc))

    def get_user_profile(self, user_id: str) -> SupabaseResult:
        """Get user profile by user_id."""
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            result = self._client.table("user_profiles").select("*").eq("user_id", user_id).execute()
            profile = result.data[0] if result.data else None
            return SupabaseResult(True, data=profile)
        except Exception as exc:  # pylint: disable=broad-except
            return SupabaseResult(False, error=str(exc))

    def update_user_profile(self, user_id: str, display_name: str = None, preferences: Dict = None) -> SupabaseResult:
        """Update user profile fields."""
        if not self._client:
            return SupabaseResult(False, error="Supabase is not configured.")

        try:
            update_data = {}
            if display_name is not None:
                update_data["display_name"] = display_name
            if preferences is not None:
                update_data["preferences"] = preferences

            result = self._client.table("user_profiles").update(update_data).eq("user_id", user_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:  # pylint: disable=broad-except
            return SupabaseResult(False, error=str(exc))
