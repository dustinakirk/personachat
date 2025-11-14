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
    PersonaEnrichment,
    PersonaRelationship
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
                "tags": enrichment.tags,
                "avatar_emoji": enrichment.avatar_emoji,
                "avatar_color": enrichment.avatar_color
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

    # ========================================================================
    # PERSONA RELATIONSHIP OPERATIONS
    # ========================================================================

    def create_relationship(self, user_id: str, from_persona_id: str, to_persona_id: str,
                          relationship_type: str, label: Optional[str] = None,
                          shared_context: Optional[str] = None,
                          interaction_style: Optional[str] = None) -> SupabaseResult:
        """Create a relationship between two personas"""
        try:
            data = {
                "user_id": user_id,
                "from_persona_id": from_persona_id,
                "to_persona_id": to_persona_id,
                "relationship_type": relationship_type,
                "label": label,
                "shared_context": shared_context,
                "interaction_style": interaction_style
            }
            result = self._client.table("persona_relationships").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_payload = api_error.json()
            logger.error("Supabase error creating relationship from %s to %s: %s",
                        from_persona_id, to_persona_id, error_payload)
            return SupabaseResult(False, error=error_payload)
        except Exception as exc:
            logger.exception("Unexpected error creating relationship")
            return SupabaseResult(False, error=str(exc))

    def create_relationships_bulk(self, user_id: str, from_persona_id: str,
                                 relationships: List[dict]) -> SupabaseResult:
        """Create multiple relationships at once (for persona creation workflow)"""
        try:
            data_list = []
            for rel in relationships:
                data_list.append({
                    "user_id": user_id,
                    "from_persona_id": from_persona_id,
                    "to_persona_id": rel["persona_id"],
                    "relationship_type": rel["relationship_type"],
                    "label": rel.get("label"),
                    "shared_context": rel.get("shared_context"),
                    "interaction_style": rel.get("interaction_style")
                })

            if not data_list:
                return SupabaseResult(True, data={"relationships": []})

            result = self._client.table("persona_relationships").insert(data_list).execute()
            return SupabaseResult(True, data={"relationships": result.data})
        except APIError as api_error:
            error_payload = api_error.json()
            logger.error("Supabase error creating bulk relationships: %s", error_payload)
            return SupabaseResult(False, error=error_payload)
        except Exception as exc:
            logger.exception("Unexpected error creating bulk relationships")
            return SupabaseResult(False, error=str(exc))

    def get_relationships(self, persona_id: str) -> SupabaseResult:
        """Get all relationships for a persona (both outgoing and incoming)"""
        try:
            # Get outgoing relationships (from this persona to others)
            outgoing = (
                self._client.table("persona_relationships")
                .select("*")
                .eq("from_persona_id", persona_id)
                .execute()
            )

            # Get incoming relationships (from others to this persona)
            incoming = (
                self._client.table("persona_relationships")
                .select("*")
                .eq("to_persona_id", persona_id)
                .execute()
            )

            outgoing_data = outgoing.data if outgoing.data else []
            incoming_data = incoming.data if incoming.data else []

            # Convert to PersonaRelationship objects
            outgoing_rels = [PersonaRelationship.from_db_row(row) for row in outgoing_data]
            incoming_rels = [PersonaRelationship.from_db_row(row) for row in incoming_data]

            return SupabaseResult(True, data={
                "outgoing": outgoing_rels,
                "incoming": incoming_rels
            })
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            logger.error("API error in get_relationships for persona_id=%s: %s",
                        persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_relationships for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def get_relationship_with_personas(self, persona_id: str) -> SupabaseResult:
        """Get relationships with full persona details for display"""
        try:
            # Get outgoing relationships with persona details
            outgoing = (
                self._client.table("persona_relationships")
                .select("*, to_persona:to_persona_id(id, name, role, company)")
                .eq("from_persona_id", persona_id)
                .execute()
            )

            # Get incoming relationships with persona details
            incoming = (
                self._client.table("persona_relationships")
                .select("*, from_persona:from_persona_id(id, name, role, company)")
                .eq("to_persona_id", persona_id)
                .execute()
            )

            return SupabaseResult(True, data={
                "outgoing": outgoing.data if outgoing.data else [],
                "incoming": incoming.data if incoming.data else []
            })
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            logger.error("API error in get_relationship_with_personas for persona_id=%s: %s",
                        persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_relationship_with_personas for persona_id=%s",
                           persona_id)
            return SupabaseResult(False, error=str(exc))

    def update_relationship(self, from_persona_id: str, to_persona_id: str,
                          updates: dict) -> SupabaseResult:
        """Update a relationship"""
        try:
            if not updates:
                return SupabaseResult(False, error="No updates provided")

            result = (
                self._client.table("persona_relationships")
                .update(updates)
                .eq("from_persona_id", from_persona_id)
                .eq("to_persona_id", to_persona_id)
                .execute()
            )
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            logger.error("API error updating relationship: %s", error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error updating relationship")
            return SupabaseResult(False, error=str(exc))

    def delete_relationship(self, from_persona_id: str, to_persona_id: str) -> SupabaseResult:
        """Delete a relationship"""
        try:
            result = (
                self._client.table("persona_relationships")
                .delete()
                .eq("from_persona_id", from_persona_id)
                .eq("to_persona_id", to_persona_id)
                .execute()
            )
            return SupabaseResult(True, data={"deleted": True})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            logger.error("API error deleting relationship: %s", error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error deleting relationship")
            return SupabaseResult(False, error=str(exc))
