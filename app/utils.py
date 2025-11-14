"""
Utility functions for PersonaChat application
"""

import re
from datetime import datetime, timedelta
from typing import Union, List, Dict
from app.models import Persona


def relative_time(timestamp: Union[str, datetime]) -> str:
    """
    Convert a timestamp to a user-friendly relative time string.

    Examples:
        - "Just now" (< 1 minute)
        - "5 minutes ago"
        - "2 hours ago"
        - "Yesterday 3:30pm"
        - "Nov 12 at 2:15pm"

    Args:
        timestamp: ISO format string or datetime object

    Returns:
        Formatted relative time string
    """
    # Convert string to datetime if needed
    if isinstance(timestamp, str):
        # Handle various timestamp formats
        try:
            # Try ISO format with timezone (from Supabase)
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try without timezone
                dt = datetime.fromisoformat(timestamp.split('+')[0].split('Z')[0])
            except (ValueError, AttributeError):
                return timestamp  # Return as-is if parsing fails
    else:
        dt = timestamp

    # Make timezone-naive for comparison (assumes local timezone)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    now = datetime.now()
    diff = now - dt

    # Just now (< 1 minute)
    if diff < timedelta(minutes=1):
        return "Just now"

    # Minutes ago (< 1 hour)
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    # Hours ago (< 24 hours)
    if diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    # Yesterday with time
    if diff < timedelta(days=2) and dt.date() == (now - timedelta(days=1)).date():
        time_str = dt.strftime("%I:%M%p").lstrip('0').lower()
        return f"Yesterday {time_str}"

    # This week (< 7 days) - show day name with time
    if diff < timedelta(days=7):
        day_name = dt.strftime("%A")
        time_str = dt.strftime("%I:%M%p").lstrip('0').lower()
        return f"{day_name} {time_str}"

    # This year - show month/day with time
    if dt.year == now.year:
        date_str = dt.strftime("%b %d")
        time_str = dt.strftime("%I:%M%p").lstrip('0').lower()
        return f"{date_str} at {time_str}"

    # Older - show full date with time
    date_str = dt.strftime("%b %d, %Y")
    time_str = dt.strftime("%I:%M%p").lstrip('0').lower()
    return f"{date_str} at {time_str}"


def match_personas_in_message(message: str, personas: List[Persona]) -> Dict[str, any]:
    """
    Algorithmic persona matching in user message.

    Detects persona references through:
    - @mentions: @sarah, @john
    - First names: "sarah thinks"
    - Last names: "ask johnson"
    - Full names: "sarah johnson"
    - Roles: "marketing director"
    - Multiple mentions: "@sarah and @john"

    Args:
        message: User's message text
        personas: List of Persona objects to match against

    Returns:
        Dict with:
            - matched_personas: List[Persona] with high-confidence matches
            - confidence: float (0-100) overall confidence score
            - method: str describing how match was made
    """
    if not personas:
        return {"matched_personas": [], "confidence": 0, "method": "no_participants"}

    message_lower = message.lower()
    matches = []
    match_methods = []

    # 1. Check for @mentions (highest priority)
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, message)

    if mentions:
        for mention in mentions:
            mention_lower = mention.lower()
            for persona in personas:
                # Check if mention matches first name or starts with persona name
                first_name = persona.name.split()[0].lower() if persona.name else ""
                if mention_lower == first_name or persona.name.lower().startswith(mention_lower):
                    if persona not in matches:
                        matches.append(persona)
                        match_methods.append(f"@mention:{persona.name}")

        if matches:
            return {
                "matched_personas": matches,
                "confidence": 100,
                "method": f"@mentions: {', '.join(match_methods)}"
            }

    # 2. Check for full name matches
    for persona in personas:
        if not persona.name:
            continue

        full_name_lower = persona.name.lower()
        if full_name_lower in message_lower:
            if persona not in matches:
                matches.append(persona)
                match_methods.append(f"full_name:{persona.name}")

    if matches:
        return {
            "matched_personas": matches,
            "confidence": 95,
            "method": f"Full name: {', '.join(match_methods)}"
        }

    # 3. Check for first name matches
    words_in_message = set(re.findall(r'\b\w+\b', message_lower))

    for persona in personas:
        if not persona.name:
            continue

        first_name = persona.name.split()[0].lower()
        if first_name in words_in_message:
            if persona not in matches:
                matches.append(persona)
                match_methods.append(f"first_name:{persona.name}")

    if matches:
        confidence = 85 if len(matches) == 1 else 75  # Lower if multiple matches
        return {
            "matched_personas": matches,
            "confidence": confidence,
            "method": f"First name: {', '.join(match_methods)}"
        }

    # 4. Check for last name matches
    for persona in personas:
        if not persona.name or len(persona.name.split()) < 2:
            continue

        last_name = persona.name.split()[-1].lower()
        if last_name in words_in_message and len(last_name) > 2:  # Avoid short names
            if persona not in matches:
                matches.append(persona)
                match_methods.append(f"last_name:{persona.name}")

    if matches:
        confidence = 80 if len(matches) == 1 else 70
        return {
            "matched_personas": matches,
            "confidence": confidence,
            "method": f"Last name: {', '.join(match_methods)}"
        }

    # 5. Check for role/title matches
    for persona in personas:
        if not persona.role:
            continue

        role_lower = persona.role.lower()
        # Check for significant role keywords (at least 3 characters)
        role_words = [word for word in role_lower.split() if len(word) >= 3]

        for role_word in role_words:
            if role_word in message_lower:
                if persona not in matches:
                    matches.append(persona)
                    match_methods.append(f"role:{persona.role}")
                break

    if matches:
        confidence = 65 if len(matches) == 1 else 55
        return {
            "matched_personas": matches,
            "confidence": confidence,
            "method": f"Role: {', '.join(match_methods)}"
        }

    # 6. Check for company matches (lower confidence)
    for persona in personas:
        if not persona.company:
            continue

        company_lower = persona.company.lower()
        if company_lower in message_lower:
            if persona not in matches:
                matches.append(persona)
                match_methods.append(f"company:{persona.company}")

    if matches:
        return {
            "matched_personas": matches,
            "confidence": 50,
            "method": f"Company: {', '.join(match_methods)}"
        }

    # No matches found
    return {
        "matched_personas": [],
        "confidence": 0,
        "method": "no_match"
    }


def should_use_ai_routing(match_result: Dict, num_participants: int) -> Dict[str, any]:
    """
    Determine if AI routing should be used based on match confidence.

    Args:
        match_result: Result from match_personas_in_message()
        num_participants: Total number of active participants

    Returns:
        Dict with:
            - use_ai_routing: bool - True if AI routing should be used
            - respond_all: bool - True if all personas should respond (generic question)
    """
    # Always use algorithmic result for high confidence matches
    if match_result["confidence"] >= 70:
        return {"use_ai_routing": False, "respond_all": False}

    # For medium confidence with multiple participants, use AI as tiebreaker
    if match_result["confidence"] >= 50 and num_participants > 2:
        return {"use_ai_routing": True, "respond_all": False}

    # For low confidence or no matches, check if it's a generic question
    if match_result["confidence"] < 50:
        # Generic question - no specific targeting detected
        # All personas should respond
        return {"use_ai_routing": False, "respond_all": True}

    return {"use_ai_routing": False, "respond_all": False}
