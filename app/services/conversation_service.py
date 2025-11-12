"""
ConversationService - Multi-persona conversation orchestration

Handles conversation creation, participant management, message routing,
and autosave functionality for multi-persona chat sessions.
"""

from typing import List, Dict, Any, Optional
from supabase import Client
from app.models import Persona, Message
from app.services.supabase_service import SupabaseResult


class ConversationService:
    """Service for multi-persona conversation operations"""

    def __init__(self, supabase_client: Client):
        self._client = supabase_client

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
        except Exception as exc:
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
            return SupabaseResult(True, data=result.data if result.data else {})
        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def delete_conversation(self, conversation_id: str) -> SupabaseResult:
        """Delete a conversation and all its messages"""
        try:
            result = self._client.table("conversations").delete().eq("id", conversation_id).execute()
            return SupabaseResult(True, data={"deleted": True})
        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def get_participants(self, conversation_id: str) -> SupabaseResult:
        """Get all participants in a conversation with persona details"""
        try:
            # Get participant records
            participants_result = (
                self._client.table("conversation_participants")
                .select("persona_id, active, joined_at")
                .eq("conversation_id", conversation_id)
                .execute()
            )

            if not participants_result.data:
                return SupabaseResult(True, data={"participants": []})

            # Get persona IDs
            persona_ids = [p["persona_id"] for p in participants_result.data]

            # Fetch full persona details
            personas_result = (
                self._client.table("personas")
                .select("*")
                .in_("id", persona_ids)
                .execute()
            )

            personas = personas_result.data if personas_result.data else []

            # Merge participant status with persona data
            participants = []
            for p in participants_result.data:
                persona = next((per for per in personas if per["id"] == p["persona_id"]), None)
                if persona:
                    participants.append({
                        **persona,
                        "active": p["active"],
                        "joined_at": p["joined_at"]
                    })

            return SupabaseResult(True, data={"participants": participants})
        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))

    def get_messages(self, conversation_id: str, limit: int = 100) -> SupabaseResult:
        """Get messages in a conversation with speaker information"""
        try:
            result = (
                self._client.table("messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at")
                .limit(limit)
                .execute()
            )

            messages = result.data if result.data else []

            # Fetch persona details for persona messages
            persona_ids = [m["persona_id"] for m in messages if m.get("persona_id")]
            personas = {}

            if persona_ids:
                personas_result = (
                    self._client.table("personas")
                    .select("id, name, role")
                    .in_("id", persona_ids)
                    .execute()
                )
                personas = {p["id"]: p for p in personas_result.data} if personas_result.data else {}

            # Enrich messages with speaker info
            enriched_messages = []
            for msg in messages:
                enriched_msg = {**msg}
                if msg.get("persona_id") and msg["persona_id"] in personas:
                    enriched_msg["speaker_name"] = personas[msg["persona_id"]]["name"]
                    enriched_msg["speaker_role"] = personas[msg["persona_id"]].get("role")
                    enriched_msg["is_user_message"] = False
                else:
                    enriched_msg["speaker_name"] = "You"
                    enriched_msg["is_user_message"] = True
                enriched_messages.append(enriched_msg)

            return SupabaseResult(True, data={"messages": enriched_messages})
        except Exception as exc:
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
        except Exception as exc:
            return SupabaseResult(False, error=str(exc))
