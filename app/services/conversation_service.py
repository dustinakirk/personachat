"""
ConversationService - Multi-persona conversation orchestration

Handles conversation creation, participant management, message routing,
and autosave functionality for multi-persona chat sessions.
"""

import logging
from typing import List, Dict, Any, Optional
from postgrest import APIError
from supabase import Client
from app.models import Persona, Message
from app.services.supabase_service import SupabaseResult

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for multi-persona conversation operations"""

    def __init__(self, authenticated_client: Client):
        self._client = authenticated_client  # Authenticated client for all operations

    # ========================================================================
    # CONVERSATION CRUD
    # ========================================================================

    def create_conversation(self, user_id: str, title: Optional[str] = None, participant_ids: List[str] = None) -> SupabaseResult:
        """
        Create a new multi-persona conversation

        Args:
            user_id: User creating the conversation
            title: Optional conversation title (auto-generated if None)
            participant_ids: List of persona IDs to add as participants

        Returns:
            SupabaseResult with conversation data
        """
        try:
            # Create conversation
            conv_data = {
                "user_id": user_id,
                "title": title
            }
            conv_result = self._client.table("conversations").insert(conv_data).execute()

            if not conv_result.data:
                return SupabaseResult(False, error="Failed to create conversation")

            conversation = conv_result.data[0]
            conversation_id = conversation["id"]

            # Add participants if provided
            if participant_ids:
                participants = [
                    {"conversation_id": conversation_id, "persona_id": pid}
                    for pid in participant_ids
                ]
                self._client.table("conversation_participants").insert(participants).execute()

            return SupabaseResult(True, data=conversation)
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in create_conversation for user_id=%s: %s", user_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in create_conversation for user_id=%s", user_id)
            return SupabaseResult(False, error=str(exc))

    def get_conversation(self, conversation_id: str) -> SupabaseResult:
        """Get a conversation by ID"""
        try:
            result = (
                self._client.table("conversations")
                .select("*")
                .eq("id", conversation_id)
                .single()
                .execute()
            )
            # If no data found, return failure instead of empty dict
            if not result.data:
                return SupabaseResult(False, error="Conversation not found")
            return SupabaseResult(True, data=result.data)
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_conversation for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_conversation for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def get_user_conversations(self, user_id: str, limit: int = 20) -> SupabaseResult:
        """Get recent conversations for a user"""
        try:
            result = (
                self._client.table("conversations")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            conversations = result.data if result.data else []
            return SupabaseResult(True, data={"conversations": conversations})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_user_conversations for user_id=%s: %s", user_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_user_conversations for user_id=%s", user_id)
            return SupabaseResult(False, error=str(exc))

    def get_conversation_by_single_participant(self, user_id: str, persona_id: str) -> SupabaseResult:
        """
        Find the most recent conversation with ONLY a single specific persona.

        This is used when clicking "Chat" on a persona to reuse existing single-persona
        conversations instead of creating duplicates. Multi-persona conversations are
        excluded to allow separate contexts.

        Args:
            user_id: User ID
            persona_id: Persona ID to search for

        Returns:
            SupabaseResult with conversation data or None if not found
        """
        try:
            # Get all user conversations with their participants (ordered by most recent)
            result = (
                self._client.table("conversations")
                .select("*, conversation_participants(persona_id)")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute()
            )

            if not result.data:
                return SupabaseResult(True, data=None)

            # Filter in Python for single-participant conversations with this persona
            for conv in result.data:
                participants = conv.get("conversation_participants", [])

                # Check if this conversation has exactly 1 participant with the matching persona_id
                if len(participants) == 1 and participants[0]["persona_id"] == persona_id:
                    # Remove embedded participants to match standard conversation format
                    conv.pop("conversation_participants", None)
                    logger.info("Found existing single-persona conversation: %s for persona: %s", conv["id"], persona_id)
                    return SupabaseResult(True, data=conv)

            # No matching single-persona conversation found
            logger.info("No existing single-persona conversation found for persona: %s", persona_id)
            return SupabaseResult(True, data=None)

        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_conversation_by_single_participant for persona_id=%s: %s", persona_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_conversation_by_single_participant for persona_id=%s", persona_id)
            return SupabaseResult(False, error=str(exc))

    def update_conversation_title(self, conversation_id: str, title: str) -> SupabaseResult:
        """Update conversation title"""
        try:
            result = (
                self._client.table("conversations")
                .update({"title": title})
                .eq("id", conversation_id)
                .execute()
            )
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in update_conversation_title for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in update_conversation_title for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def update_conversation_context(self, conversation_id: str, context: str) -> SupabaseResult:
        """
        Update conversation context - background information that informs persona responses

        Args:
            conversation_id: ID of the conversation
            context: User-provided context text to help personas understand the scenario

        Returns:
            SupabaseResult with updated conversation data
        """
        try:
            result = (
                self._client.table("conversations")
                .update({"context": context})
                .eq("id", conversation_id)
                .execute()
            )
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in update_conversation_context for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in update_conversation_context for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def delete_conversation(self, conversation_id: str) -> SupabaseResult:
        """Delete a conversation and all its messages"""
        try:
            result = self._client.table("conversations").delete().eq("id", conversation_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in delete_conversation for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in delete_conversation for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    # ========================================================================
    # PARTICIPANT MANAGEMENT
    # ========================================================================

    def add_participant(self, conversation_id: str, persona_id: str) -> SupabaseResult:
        """Add a persona to a conversation"""
        try:
            data = {
                "conversation_id": conversation_id,
                "persona_id": persona_id,
                "active": True
            }
            result = self._client.table("conversation_participants").insert(data).execute()
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in add_participant for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in add_participant for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def remove_participant(self, conversation_id: str, persona_id: str) -> SupabaseResult:
        """Remove a persona from a conversation"""
        try:
            result = (
                self._client.table("conversation_participants")
                .delete()
                .eq("conversation_id", conversation_id)
                .eq("persona_id", persona_id)
                .execute()
            )
            return SupabaseResult(True, data={"removed": True})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in remove_participant for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in remove_participant for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def toggle_participant(self, conversation_id: str, persona_id: str, active: bool) -> SupabaseResult:
        """Toggle a participant's active status (mute/unmute mid-conversation)"""
        try:
            result = (
                self._client.table("conversation_participants")
                .update({"active": active})
                .eq("conversation_id", conversation_id)
                .eq("persona_id", persona_id)
                .execute()
            )
            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in toggle_participant for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in toggle_participant for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def get_participants(self, conversation_id: str) -> SupabaseResult:
        """Get all participants in a conversation with persona details"""
        try:
            # Use join to fetch participants and persona details in a single query
            participants_result = (
                self._client.table("conversation_participants")
                .select("persona_id, active, joined_at, personas(*)")
                .eq("conversation_id", conversation_id)
                .execute()
            )

            if not participants_result.data:
                return SupabaseResult(True, data={"participants": []})

            # Flatten the joined data structure
            participants = []
            for p in participants_result.data:
                if p.get("personas"):
                    participants.append({
                        **p["personas"],
                        "active": p["active"],
                        "joined_at": p["joined_at"]
                    })

            return SupabaseResult(True, data={"participants": participants})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_participants for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_participants for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    # ========================================================================
    # MESSAGE MANAGEMENT
    # ========================================================================

    def add_user_message(self, conversation_id: str, user_id: str, content: str) -> SupabaseResult:
        """Add a user message to the conversation"""
        try:
            data = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "persona_id": None,  # User message
                "content": content
            }
            result = self._client.table("messages").insert(data).execute()

            # Update conversation updated_at timestamp
            self._client.table("conversations").update({"updated_at": "NOW()"}).eq("id", conversation_id).execute()

            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in add_user_message for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in add_user_message for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def add_persona_message(self, conversation_id: str, persona_id: str, content: str) -> SupabaseResult:
        """Add a persona response to the conversation"""
        try:
            data = {
                "conversation_id": conversation_id,
                "persona_id": persona_id,
                "user_id": None,  # Persona message
                "content": content
            }
            result = self._client.table("messages").insert(data).execute()

            # Update conversation updated_at timestamp
            self._client.table("conversations").update({"updated_at": "NOW()"}).eq("id", conversation_id).execute()

            return SupabaseResult(True, data=result.data[0] if result.data else {})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in add_persona_message for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in add_persona_message for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    def get_messages(self, conversation_id: str, limit: int = 100, order_desc: bool = False) -> SupabaseResult:
        """Get messages in a conversation with speaker information"""
        try:
            # Use join to fetch messages with persona details in a single query
            query = (
                self._client.table("messages")
                .select("*, personas(id, name, role)")
                .eq("conversation_id", conversation_id)
            )

            # Apply ordering based on order_desc parameter
            if order_desc:
                query = query.order("created_at", desc=True)
            else:
                query = query.order("created_at")

            result = query.limit(limit).execute()

            messages = result.data if result.data else []

            # Enrich messages with speaker info
            enriched_messages = []
            for msg in messages:
                enriched_msg = {**msg}
                if msg.get("persona_id") and msg.get("personas"):
                    enriched_msg["speaker_name"] = msg["personas"]["name"]
                    enriched_msg["speaker_role"] = msg["personas"].get("role")
                    enriched_msg["is_user_message"] = False
                else:
                    enriched_msg["speaker_name"] = "You"
                    enriched_msg["is_user_message"] = True
                # Remove the nested personas object to keep the message structure clean
                enriched_msg.pop("personas", None)
                enriched_messages.append(enriched_msg)

            return SupabaseResult(True, data={"messages": enriched_messages})
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_messages for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_messages for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))

    # ========================================================================
    # CONVERSATION HELPERS
    # ========================================================================

    def generate_conversation_title(self, messages: List[Dict[str, Any]]) -> str:
        """
        Generate a conversation title from the first user message

        Args:
            messages: List of message dictionaries

        Returns:
            Generated title string
        """
        if not messages:
            return "New Conversation"

        # Find first user message
        first_user_msg = next((m for m in messages if m.get("user_id")), None)

        if not first_user_msg:
            return "New Conversation"

        content = first_user_msg.get("content", "")
        # Take first 50 characters
        title = content[:50]
        if len(content) > 50:
            title += "..."

        return title or "New Conversation"

    def get_conversation_summary(self, conversation_id: str) -> SupabaseResult:
        """
        Get conversation summary including participants and last message

        Args:
            conversation_id: Conversation ID

        Returns:
            SupabaseResult with summary data
        """
        try:
            # Get conversation
            conv_result = self.get_conversation(conversation_id)
            if not conv_result.success:
                return conv_result

            conversation = conv_result.data

            # Get participants
            participants_result = self.get_participants(conversation_id)
            participants = participants_result.data.get("participants", []) if participants_result.success else []

            # Get last message
            messages_result = (
                self._client.table("messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            last_message = messages_result.data[0] if messages_result.data else None

            summary = {
                **conversation,
                "participants": participants,
                "last_message": last_message,
                "participant_count": len(participants)
            }

            return SupabaseResult(True, data=summary)
        except APIError as api_error:
            error_dict = api_error.json() if hasattr(api_error, 'json') else {}
            error_code = error_dict.get('code', '')
            if error_code in ['PGRST301', 'PGRST302', 'PGRST303'] or 'JWT expired' in str(api_error):
                raise
            logger.error("API error in get_conversation_summary for conversation_id=%s: %s", conversation_id, error_dict)
            return SupabaseResult(False, error=error_dict)
        except Exception as exc:
            logger.exception("Error in get_conversation_summary for conversation_id=%s", conversation_id)
            return SupabaseResult(False, error=str(exc))
