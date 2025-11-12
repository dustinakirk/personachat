from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Generator, Optional, List, Dict, Any

from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    RetryError
)

from app.models import PersonaEnrichment, Persona, RelationshipSuggestion


@dataclass
class GeminiResult:
    """Result object for Gemini API calls."""
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None


def _is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Retries on: 503, 429, timeouts, connection errors
    No retry on: 400, 401, 403, JSON errors, missing API key
    """
    error_msg = str(exception).lower()

    # Retryable patterns
    retryable_patterns = [
        '503', 'service unavailable', 'unavailable', 'overloaded',
        '429', 'rate limit', 'quota',
        'timeout', 'timed out',
        'connection', 'network',
        'temporary', 'transient'
    ]

    # Check if any retryable pattern is in error message
    if any(pattern in error_msg for pattern in retryable_patterns):
        return True

    # Non-retryable conditions
    non_retryable = ['400', '401', '403', '404', 'json', 'parse', 'api key']
    if any(pattern in error_msg for pattern in non_retryable):
        return False

    # Default: don't retry unknown errors
    return False


def _make_api_call_with_retry(client: genai.Client, model: str, contents: str, config: types.GenerateContentConfig):
    """
    Make a Gemini API call with automatic retry on transient errors.

    Retry strategy:
    - 3 attempts total (initial + 2 retries)
    - Exponential backoff: ~1s, ~2s, ~4s
    - Only retries on 503, 429, and connection errors
    """
    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    def _call():
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

    return _call()


class GeminiService:
    """Service for interacting with Google Gemini AI models using the new GenAI SDK."""

    # Available models
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    GEMINI_2_5_PRO = "gemini-2.5-pro"

    def __init__(
        self,
        api_key: str,
        default_model: str = GEMINI_2_5_FLASH,
        system_instruction: Optional[str] = None,
    ) -> None:
        """
        Initialize the Gemini service.

        Args:
            api_key: Google AI API key
            default_model: Default model to use (default: gemini-2.5-flash)
            system_instruction: Optional system instruction for AI personality
        """
        self._api_key = api_key
        self._default_model = default_model
        self._system_instruction = system_instruction
        self._client: Optional[genai.Client] = None

        if api_key:
            try:
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini client: {e}")
                self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self._client is not None

    @property
    def default_model(self) -> str:
        """Get the default model name."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Get list of available models."""
        return [
            self.GEMINI_2_5_FLASH,
            self.GEMINI_2_0_FLASH_EXP,
            self.GEMINI_2_5_PRO,
        ]

    def set_system_instruction(self, instruction: str) -> None:
        """
        Set or update the system instruction.

        Args:
            instruction: System instruction text
        """
        self._system_instruction = instruction

    def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> GeminiResult:
        """
        Generate a response from Gemini.

        Args:
            prompt: User prompt
            model: Model to use (defaults to service default)
            stream: Whether to stream the response (not used in this method)

        Returns:
            GeminiResult with success status and response data or error
        """
        if not self._client:
            return GeminiResult(
                success=False,
                error="Gemini API key is missing. Set GEMINI_API_KEY.",
            )

        if not prompt.strip():
            return GeminiResult(success=True, data="")

        # Use default model if none specified
        model_name = model or self._default_model

        try:
            # Build config with system instruction if available
            config = types.GenerateContentConfig()
            if self._system_instruction:
                config.system_instruction = self._system_instruction

            # Use retry wrapper for API call
            response = _make_api_call_with_retry(
                self._client,
                model_name,
                prompt,
                config
            )

            # Extract text from response
            response_text = response.text if hasattr(response, 'text') else str(response)

            return GeminiResult(
                success=True,
                data=response_text or "No response returned from Gemini.",
            )

        except RetryError as e:
            last_exception = e.last_attempt.exception()
            return GeminiResult(
                success=False,
                error=f"Gemini API unavailable after 3 attempts: {str(last_exception)}",
            )
        except Exception as e:
            return GeminiResult(
                success=False,
                error=f"Gemini API error: {str(e)}",
            )

    def generate_streaming_response(
        self,
        prompt: str,
        model: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from Gemini.

        Args:
            prompt: User prompt
            model: Model to use (defaults to service default)

        Yields:
            Text chunks as they are generated

        Raises:
            RuntimeError: If the service is not configured
        """
        if not self._client:
            raise RuntimeError("Gemini API key is missing. Set GEMINI_API_KEY.")

        if not prompt.strip():
            return

        # Use default model if none specified
        model_name = model or self._default_model

        try:
            # Build config with system instruction if available
            config = types.GenerateContentConfig()
            if self._system_instruction:
                config.system_instruction = self._system_instruction

            # Generate streaming response
            response_stream = self._client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=config,
            )

            # Yield text chunks as they arrive
            for chunk in response_stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {str(e)}"

    # ========================================================================
    # PERSONA ENRICHMENT METHODS
    # ========================================================================

    def generate_persona_enrichment(self, description: str,
                                   existing_personas: Optional[List[Persona]] = None,
                                   model: Optional[str] = None) -> GeminiResult:
        """
        Generate a structured persona profile from a free-form description.
        When existing personas are provided, AI detects relevant relationships.

        Args:
            description: User's free-form persona description
            existing_personas: List of existing personas to check for relationships
            model: Model to use (defaults to service default)

        Returns:
            GeminiResult containing PersonaEnrichment data (with suggested_relationships) or error
        """
        if not self._client:
            return GeminiResult(success=False, error="Gemini API key is missing.")

        # Build context about existing personas
        existing_context = ""
        if existing_personas:
            existing_context = "\n\nEXISTING PERSONAS:\n"
            for p in existing_personas:
                existing_context += f"""
- ID: {p.id}
  Name: {p.name}
  Role: {p.role or 'Unknown'}
  Company: {p.company or 'N/A'}
  Goals: {', '.join(p.goals[:2]) if p.goals else 'N/A'}
  Tags: {', '.join(p.tags) if p.tags else 'N/A'}
"""

        prompt = f"""You are a persona creation assistant. Based on the following description, create a detailed persona profile.

Description: {description}
{existing_context}

Your tasks:
1. Create a detailed persona profile based on the description
2. If EXISTING PERSONAS are provided, analyze if this new persona has meaningful relationships with any of them:
   - Consider location, industry, role connections, collaboration potential
   - Only suggest relationships that make sense given the context
   - Provide rich details about shared context and interaction style

Return a JSON object with the following structure (use null for any fields you can't determine):
{{
    "name": "Full name of the persona",
    "role": "Job title or role",
    "company": "Company name or context (null if not applicable)",
    "age_stage": "Age range or life stage (e.g., '30s', 'early career', null if unknown)",
    "goals": ["Goal 1", "Goal 2", "Goal 3"],
    "pains": ["Pain point 1", "Pain point 2", "Pain point 3"],
    "behaviors": "Brief description of key behaviors and traits",
    "tools": "Tools, systems, or technologies they use",
    "quotes": ["Quote that captures their mindset", "Another representative quote"],
    "tags": ["tag1", "tag2", "tag3"],
    "suggested_relationships": [
        {{
            "persona_id": "UUID of related existing persona",
            "persona_name": "Name of the related persona",
            "relationship_type": "colleague|supervisor|subordinate|friend|partner|collaborator|rival|mentor|mentee",
            "shared_context": "Detailed description of shared history, location, experiences, or background (2-3 sentences)",
            "interaction_style": "How these personas typically interact, their dynamic (1-2 sentences)"
        }}
    ]
}}

IMPORTANT:
- Only include suggested_relationships if there are meaningful connections
- If no relationships make sense, use an empty array []
- Ensure consistency with existing personas (same city, related industries, etc.)
- Be specific and detailed in shared_context and interaction_style

Provide ONLY the JSON object, no additional text."""

        try:
            model_name = model or self._default_model
            config = types.GenerateContentConfig()

            # Use retry wrapper for API call
            response = _make_api_call_with_retry(
                self._client,
                model_name,
                prompt,
                config
            )

            response_text = response.text if hasattr(response, 'text') else str(response)

            # Try to parse JSON from response
            # Remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            data = json.loads(cleaned_response)

            # Parse suggested relationships
            suggested_relationships = []
            if "suggested_relationships" in data and data["suggested_relationships"]:
                for rel_data in data["suggested_relationships"]:
                    suggested_relationships.append(
                        RelationshipSuggestion(
                            persona_id=rel_data.get("persona_id", ""),
                            persona_name=rel_data.get("persona_name", ""),
                            relationship_type=rel_data.get("relationship_type", "colleague"),
                            shared_context=rel_data.get("shared_context", ""),
                            interaction_style=rel_data.get("interaction_style", "")
                        )
                    )

            # Create PersonaEnrichment from parsed data
            enrichment = PersonaEnrichment(
                name=data.get("name", "Unnamed Persona"),
                role=data.get("role", ""),
                company=data.get("company"),
                age_stage=data.get("age_stage"),
                goals=data.get("goals", []),
                pains=data.get("pains", []),
                behaviors=data.get("behaviors"),
                tools=data.get("tools"),
                quotes=data.get("quotes", []),
                tags=data.get("tags", []),
                suggested_relationships=suggested_relationships
            )

            return GeminiResult(success=True, data=enrichment)

        except RetryError as e:
            # Exhausted all retries
            last_exception = e.last_attempt.exception()
            return GeminiResult(success=False, error=f"Gemini API unavailable after 3 attempts: {str(last_exception)}")
        except json.JSONDecodeError as e:
            return GeminiResult(success=False, error=f"Failed to parse persona data: {str(e)}")
        except Exception as e:
            return GeminiResult(success=False, error=f"Gemini API error: {str(e)}")

    # ========================================================================
    # MULTI-PERSONA CHAT METHODS
    # ========================================================================

    def generate_persona_response(
        self,
        persona: Persona,
        user_message: str,
        chat_history: List[Dict[str, Any]],
        other_personas: List[Persona],
        relationships: Optional[Dict[str, Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> GeminiResult:
        """
        Generate a response from a specific persona in a multi-persona chat.

        Args:
            persona: The persona generating the response
            user_message: The user's latest message
            chat_history: Recent chat messages for context
            other_personas: Other personas in the conversation
            relationships: Dict mapping persona_id to relationship data (type, shared_context, interaction_style)
            model: Model to use (defaults to service default)

        Returns:
            GeminiResult containing the persona's response text or error
        """
        if not self._client:
            return GeminiResult(success=False, error="Gemini API key is missing.")

        # Build persona context
        persona_context = f"""You are roleplaying as the following persona:

Name: {persona.name}
Role: {persona.role or 'Professional'}
Company: {persona.company or 'N/A'}
Goals: {', '.join(persona.goals) if persona.goals else 'General professional success'}
Pain Points: {', '.join(persona.pains) if persona.pains else 'Common workplace challenges'}
Behaviors: {persona.behaviors or 'Professional and collaborative'}
Tools: {persona.tools or 'Standard workplace tools'}
"""

        if persona.quotes:
            persona_context += f"\nTypical phrases: {', '.join(persona.quotes)}"

        # Build context about other personas WITH relationship information
        other_context = ""
        if other_personas:
            other_context = "\n\nOther personas in this conversation:\n"
            for p in other_personas:
                other_context += f"- {p.name} ({p.role or 'Professional'})"

                # Add relationship context if available
                if relationships and p.id in relationships:
                    rel = relationships[p.id]
                    other_context += f"\n  Relationship: {rel.get('relationship_type', 'colleague')}"
                    if rel.get('shared_context'):
                        other_context += f"\n  Shared context: {rel.get('shared_context')}"
                    if rel.get('interaction_style'):
                        other_context += f"\n  How you interact: {rel.get('interaction_style')}"
                other_context += "\n"

        # Build chat history context
        history_context = ""
        if chat_history:
            history_context = "\n\nRecent conversation:\n"
            for msg in chat_history[-10:]:  # Last 10 messages
                speaker = msg.get("speaker", "User")
                content = msg.get("content", "")
                history_context += f"{speaker}: {content}\n"

        prompt = f"""{persona_context}{other_context}{history_context}

User's message: {user_message}

Respond as {persona.name} would, staying in character. Keep your response concise (2-4 sentences) and relevant to the conversation.

IMPORTANT:
- Reference your relationships with other personas naturally when relevant
- You can respond to or acknowledge other personas' messages, not just the user
- Use shared context and interaction styles when addressing personas you have relationships with
- Stay authentic to your character and the established relationships"""

        try:
            model_name = model or self._default_model
            config = types.GenerateContentConfig()

            # Use retry wrapper for API call
            response = _make_api_call_with_retry(
                self._client,
                model_name,
                prompt,
                config
            )

            response_text = response.text if hasattr(response, 'text') else str(response)

            return GeminiResult(success=True, data=response_text.strip())

        except RetryError as e:
            last_exception = e.last_attempt.exception()
            return GeminiResult(success=False, error=f"Gemini API unavailable after 3 attempts: {str(last_exception)}")
        except Exception as e:
            return GeminiResult(success=False, error=f"Gemini API error: {str(e)}")

    def route_message_to_personas(
        self,
        user_message: str,
        participant_personas: List[Persona],
        chat_history: List[Dict[str, Any]],
        max_responders: int = 3,
        model: Optional[str] = None
    ) -> GeminiResult:
        """
        Determine which personas should respond to a user message.

        Args:
            user_message: The user's message
            participant_personas: All personas in the conversation
            chat_history: Recent chat messages for context
            max_responders: Maximum number of personas to respond (default: 3)
            model: Model to use (defaults to service default)

        Returns:
            GeminiResult containing list of persona IDs who should respond
        """
        if not self._client:
            return GeminiResult(success=False, error="Gemini API key is missing.")

        # Build persona list
        personas_list = ""
        for i, p in enumerate(participant_personas):
            personas_list += f"{i+1}. {p.name} ({p.role or 'Professional'}) - ID: {p.id}\n"
            if p.goals:
                personas_list += f"   Goals: {', '.join(p.goals[:2])}\n"

        # Build chat context
        history_context = ""
        if chat_history:
            history_context = "\n\nRecent conversation:\n"
            for msg in chat_history[-5:]:  # Last 5 messages
                speaker = msg.get("speaker", "User")
                content = msg.get("content", "")
                history_context += f"{speaker}: {content}\n"

        prompt = f"""You are a conversation router. Determine which personas should respond to the user's message based on relevance.

Personas in conversation:
{personas_list}{history_context}

User's message: {user_message}

Select up to {max_responders} personas who should respond. Consider:
1. Expertise relevance to the topic
2. Conversational flow (who was addressed or mentioned)
3. Diversity of perspectives

Return a JSON array of persona IDs who should respond, ordered by priority:
["persona-id-1", "persona-id-2", ...]

If the message mentions a persona by name (e.g., "@PersonaName"), prioritize that persona.
Provide ONLY the JSON array, no additional text."""

        try:
            model_name = model or self._default_model
            config = types.GenerateContentConfig()

            # Use retry wrapper for API call
            response = _make_api_call_with_retry(
                self._client,
                model_name,
                prompt,
                config
            )

            response_text = response.text if hasattr(response, 'text') else str(response)

            # Clean and parse JSON
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            persona_ids = json.loads(cleaned_response)

            return GeminiResult(success=True, data=persona_ids[:max_responders])

        except RetryError as e:
            # Fallback: return first persona if routing fails after retries
            last_exception = e.last_attempt.exception()
            print(f"Routing failed after retries: {last_exception}")
            first_persona_id = participant_personas[0].id if participant_personas else None
            return GeminiResult(success=True, data=[first_persona_id] if first_persona_id else [])
        except json.JSONDecodeError as e:
            # Fallback: return first persona if routing fails
            fallback_ids = [participant_personas[0].id] if participant_personas else []
            return GeminiResult(success=True, data=fallback_ids)
        except Exception as e:
            return GeminiResult(success=False, error=f"Gemini API error: {str(e)}")
