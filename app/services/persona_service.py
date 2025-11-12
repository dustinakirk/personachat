"""
PersonaService - Business logic for persona management

Handles CRUD operations, enrichment coordination, and relationship management
for personas and persona groups.
"""

import logging
from typing import List, Optional

from postgrest import APIError
from supabase import Client
from app.models import (
    Persona, PersonaGroup, PersonaRelationship,
    PersonaEnrichment, PersonaSuggestion
)
from app.services.supabase_service import SupabaseResult, SupabaseService

logger = logging.getLogger(__name__)

class PersonaService:
    """Service for persona and persona group operations"""

    def __init__(self, supabase_client: Client, supabase_service: SupabaseService = None):
        self._client = supabase_client  # Default client for reads
        self._supabase_service = supabase_service  # For creating authenticated clients

    # ========================================================================
    # PERSONA GROUP OPERATIONS
    # ========================================================================

    def create_persona_group(self, user_id: str, name: str, description: Optional[str] = None, access_token: Optional[str] = None) -> SupabaseResult:
        """Create a new persona group"""
        try:
            # Use authenticated client if access_token provided
            client = self._client
            if self._supabase_service:
                if not access_token:
                    logger.warning("Access token missing when creating persona group for user_id=%s", user_id)
                    return SupabaseResult(False, error="Authentication required to create persona groups.")
                client = self._supabase_service.get_authenticated_client(access_token)
                if not client:
                    logger.error("Failed to create authenticated Supabase client for persona group (user_id=%s)", user_id)
                    return SupabaseResult(False, error="Failed to authenticate Supabase request.")

            data = {
                "user_id": user_id,
                "name": name,
                "description": description
            }
            result = client.table("persona_groups").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_payload = api_error.json()
            logger.error("Supabase error creating persona group for user_id=%s: %s", user_id, error_payload)
            return SupabaseResult(False, error=error_payload)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error creating persona group for user_id=%s", user_id)
            return SupabaseResult(False, error=str(exc))

    def get_persona_groups(self, user_id: str) -> SupabaseResult:
        """Get all persona groups for a user"""
        try:
            result = (
                self._client.table("persona_groups")
                .select("*")
                .eq("user_id", user_id)
                .order("name")
                .execute()
            )
            return SupabaseResult(True, data={"groups": result.data if result.data else []})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def update_persona_group(self, group_id: str, name: Optional[str] = None, description: Optional[str] = None) -> SupabaseResult:
        """Update a persona group"""
        try:
            updates = {}
            if name is not None:
                updates["name"] = name
            if description is not None:
                updates["description"] = description

            if not updates:
                return SupabaseResult(False, error="No updates provided")

            result = self._client.table("persona_groups").update(updates).eq("id", group_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def delete_persona_group(self, group_id: str) -> SupabaseResult:
        """Delete a persona group (sets personas to NULL group_id)"""
        try:
            result = self._client.table("persona_groups").delete().eq("id", group_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    # ========================================================================
    # PERSONA CRUD OPERATIONS
    # ========================================================================

    def create_persona(self, user_id: str, enrichment: PersonaEnrichment, group_id: Optional[str] = None, access_token: Optional[str] = None) -> SupabaseResult:
        """Create a new persona from enrichment data"""
        try:
            # Use authenticated client if access_token provided
            client = self._client
            if self._supabase_service:
                if not access_token:
                    logger.error("Access token missing when creating persona for user_id=%s", user_id)
                    return SupabaseResult(False, error="Authentication required: No access token in session. Please log out and log back in.")

                logger.info("Attempting to create authenticated client for persona creation (user_id=%s)", user_id)
                client = self._supabase_service.get_authenticated_client(access_token)

                if not client:
                    logger.error("Failed to create authenticated Supabase client for persona creation (user_id=%s)", user_id)
                    return SupabaseResult(False, error="Failed to authenticate Supabase request. Please check server logs for details, or try logging out and back in.")

            data = {
                "user_id": user_id,
                "group_id": group_id,
                "name": enrichment.name,
                "role": enrichment.role,
                "company": enrichment.company,
                "age_stage": enrichment.age_stage,
                "goals": enrichment.goals,
                "pains": enrichment.pains,
                "behaviors": enrichment.behaviors,
                "tools": enrichment.tools,
                "quotes": enrichment.quotes,
                "tags": enrichment.tags
            }
            result = client.table("personas").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_payload = api_error.json()
            logger.error("Supabase error creating persona for user_id=%s: %s", user_id, error_payload)
            return SupabaseResult(False, error=error_payload)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error creating persona for user_id=%s", user_id)
            return SupabaseResult(False, error=str(exc))

    def get_persona(self, persona_id: str) -> SupabaseResult:
        """Get a single persona by ID"""
        try:
            result = (
                self._client.table("personas")
                .select("*")
                .eq("id", persona_id)
                .single()
                .execute()
            )
            return SupabaseResult(True, data=result.data if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def get_personas(self, user_id: str, group_id: Optional[str] = None, include_archived: bool = False) -> SupabaseResult:
        """Get all personas for a user, optionally filtered by group"""
        try:
            query = self._client.table("personas").select("*").eq("user_id", user_id)

            if group_id is not None:
                query = query.eq("group_id", group_id)

            if not include_archived:
                query = query.eq("archived", False)

            result = query.order("name").execute()
            personas = result.data if result.data else []
            return SupabaseResult(True, data={"personas": personas})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def search_personas(self, user_id: str, search_term: str, include_archived: bool = False) -> SupabaseResult:
        """Search personas by name, role, company, or tags"""
        try:
            query = self._client.table("personas").select("*").eq("user_id", user_id)

            if not include_archived:
                query = query.eq("archived", False)

            # Use ilike for case-insensitive search (Postgres specific)
            # Search in name, role, and company fields
            result = query.or_(f"name.ilike.%{search_term}%,role.ilike.%{search_term}%,company.ilike.%{search_term}%").execute()

            personas = result.data if result.data else []
            return SupabaseResult(True, data={"personas": personas})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def update_persona(self, persona_id: str, updates: dict) -> SupabaseResult:
        """Update a persona with arbitrary field updates"""
        try:
            if not updates:
                return SupabaseResult(False, error="No updates provided")

            result = self._client.table("personas").update(updates).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def archive_persona(self, persona_id: str) -> SupabaseResult:
        """Archive a persona (soft delete)"""
        try:
            result = self._client.table("personas").update({"archived": True}).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def unarchive_persona(self, persona_id: str) -> SupabaseResult:
        """Unarchive a persona"""
        try:
            result = self._client.table("personas").update({"archived": False}).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def delete_persona(self, persona_id: str) -> SupabaseResult:
        """Permanently delete a persona"""
        try:
            result = self._client.table("personas").delete().eq("id", persona_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    # ========================================================================
    # PERSONA RELATIONSHIP OPERATIONS
    # ========================================================================

    def create_relationship(
        self,
        user_id: str,
        from_persona_id: str,
        to_persona_id: str,
        relationship_type: str,
        label: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SupabaseResult:
        """Create a relationship between two personas"""
        try:
            data = {
                "user_id": user_id,
                "from_persona_id": from_persona_id,
                "to_persona_id": to_persona_id,
                "relationship_type": relationship_type,
                "label": label or relationship_type,  # Default label to type
                "notes": notes
            }
            result = self._client.table("persona_relationships").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def get_persona_relationships(self, persona_id: str) -> SupabaseResult:
        """Get all relationships for a persona (both incoming and outgoing)"""
        try:
            # Get outgoing relationships
            outgoing = (
                self._client.table("persona_relationships")
                .select("*")
                .eq("from_persona_id", persona_id)
                .execute()
            )

            # Get incoming relationships
            incoming = (
                self._client.table("persona_relationships")
                .select("*")
                .eq("to_persona_id", persona_id)
                .execute()
            )

            all_relationships = []
            if outgoing.data:
                all_relationships.extend(outgoing.data)
            if incoming.data:
                all_relationships.extend(incoming.data)

            return SupabaseResult(True, data={"relationships": all_relationships})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def update_relationship(self, relationship_id: str, updates: dict) -> SupabaseResult:
        """Update a relationship (e.g., change label or type)"""
        try:
            if not updates:
                return SupabaseResult(False, error="No updates provided")

            result = self._client.table("persona_relationships").update(updates).eq("id", relationship_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def delete_relationship(self, relationship_id: str) -> SupabaseResult:
        """Delete a relationship between personas"""
        try:
            result = self._client.table("persona_relationships").delete().eq("id", relationship_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))
