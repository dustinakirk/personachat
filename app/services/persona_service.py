"""
PersonaService - Business logic for persona management

Handles CRUD operations and enrichment coordination for personas.
"""

import logging
from typing import List, Optional

from postgrest import APIError
from supabase import Client
from app.models import (
    Persona,
    PersonaEnrichment
)
from app.services.supabase_service import SupabaseResult

logger = logging.getLogger(__name__)

class PersonaService:
    """Service for persona operations"""

    def __init__(self, authenticated_client: Client):
        self._client = authenticated_client  # Authenticated client for all operations

    # ========================================================================
    # PERSONA CRUD OPERATIONS
    # ========================================================================

    def create_persona(self, user_id: str, enrichment: PersonaEnrichment) -> SupabaseResult:
        """Create a new persona from enrichment data"""
        try:
            data = {
                "user_id": user_id,
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
            result = self._client.table("personas").insert(data).execute()
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
            raw_persona = result.data if result.data else None
            if raw_persona:
                # Convert to Persona object
                persona = Persona.from_db_row(raw_persona)
                return SupabaseResult(True, data=persona)
            return SupabaseResult(False, error="Persona not found")
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_persona for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_persona for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def get_personas(self, user_id: str, include_archived: bool = False) -> SupabaseResult:
        """Get all personas for a user"""
        try:
            query = self._client.table("personas").select("*").eq("user_id", user_id)

            if not include_archived:
                query = query.eq("archived", False)

            result = query.order("name").execute()
            raw_personas = result.data if result.data else []
            # Convert raw dicts to Persona objects
            personas = [Persona.from_db_row(row) for row in raw_personas]
            logger.info("get_personas returned %d personas for user_id=%s", len(personas), user_id)
            return SupabaseResult(True, data={"personas": personas})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_personas for user_id=%s: %s", user_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_personas for user_id=%s", user_id)
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

            raw_personas = result.data if result.data else []
            # Convert raw dicts to Persona objects
            personas = [Persona.from_db_row(row) for row in raw_personas]
            logger.info("search_personas returned %d personas for user_id=%s", len(personas), user_id)
            return SupabaseResult(True, data={"personas": personas})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in search_personas for user_id=%s: %s", user_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in search_personas for user_id=%s", user_id)
            return SupabaseResult(False, error=str(exc))

    def update_persona(self, persona_id: str, updates: dict) -> SupabaseResult:
        """Update a persona with arbitrary field updates"""
        try:
            if not updates:
                return SupabaseResult(False, error="No updates provided")

            result = self._client.table("personas").update(updates).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in update_persona for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in update_persona for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def archive_persona(self, persona_id: str) -> SupabaseResult:
        """Archive a persona (soft delete)"""
        try:
            result = self._client.table("personas").update({"archived": True}).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in archive_persona for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in archive_persona for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def unarchive_persona(self, persona_id: str) -> SupabaseResult:
        """Unarchive a persona"""
        try:
            result = self._client.table("personas").update({"archived": False}).eq("id", persona_id).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in unarchive_persona for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in unarchive_persona for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def delete_persona(self, persona_id: str) -> SupabaseResult:
        """Permanently delete a persona"""
        try:
            result = self._client.table("personas").delete().eq("id", persona_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in delete_persona for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in delete_persona for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))
