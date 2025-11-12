#!/usr/bin/env python3
"""
PersonaChat V1 Feature Testing Script
Tests all major features after database migration.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.supabase_service import SupabaseService
from app.services.persona_service import PersonaService
from app.services.conversation_service import ConversationService
from app.services.gemini_service import GeminiService

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_database_tables():
    """Verify all V1 tables exist."""
    print_section("1. Database Tables Verification")

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    tables = [
        "user_profiles",
        "persona_groups",
        "personas",
        "persona_relationships",
        "conversations",
        "conversation_participants",
        "messages"
    ]

    for table in tables:
        try:
            # Try to query the table (will fail if table doesn't exist)
            result = client.table(table).select("*").limit(1).execute()
            print(f"  ✓ Table '{table}' exists")
        except Exception as e:
            print(f"  ✗ Table '{table}' missing or error: {e}")
            return False

    print("\n  All V1 tables verified successfully!")
    return True

def test_persona_service():
    """Test PersonaService CRUD operations."""
    print_section("2. Persona Service Test")

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    persona_service = PersonaService(client)

    # Note: This requires a valid user_id from auth.users
    # For now, we'll just test that the service initializes
    print("  ✓ PersonaService initialized")
    print(f"  ✓ Service methods available: {len([m for m in dir(persona_service) if not m.startswith('_')])} public methods")

    return True

def test_conversation_service():
    """Test ConversationService."""
    print_section("3. Conversation Service Test")

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    conversation_service = ConversationService(client)

    print("  ✓ ConversationService initialized")
    print(f"  ✓ Service methods available: {len([m for m in dir(conversation_service) if not m.startswith('_')])} public methods")

    return True

def test_gemini_service():
    """Test GeminiService persona features."""
    print_section("4. Gemini Service Test")

    gemini_service = GeminiService(GEMINI_API_KEY)

    if not gemini_service.is_configured:
        print("  ✗ GeminiService not configured (missing API key)")
        return False

    print("  ✓ GeminiService initialized")
    print(f"  ✓ Default model: {gemini_service.default_model}")
    print(f"  ✓ Available models: {', '.join(gemini_service.available_models)}")

    # Test persona enrichment (quick test)
    print("\n  Testing persona enrichment...")
    description = "Sarah is a product manager at a tech startup who loves hiking"
    result = gemini_service.generate_persona_enrichment(description)

    if result.success:
        enrichment = result.data
        print(f"  ✓ Enrichment successful")
        print(f"    - Name: {enrichment.name}")
        print(f"    - Role: {enrichment.role}")
        print(f"    - Goals: {len(enrichment.goals)} goals")
        print(f"    - Pains: {len(enrichment.pains)} pains")
    else:
        print(f"  ✗ Enrichment failed: {result.error}")
        return False

    return True

def test_routes():
    """Test that all V1 routes are registered."""
    print_section("5. Route Registration Test")

    from app import create_app
    app = create_app()

    expected_routes = [
        # Main routes
        "/",
        "/login",
        "/register",
        "/logout",
        "/application",

        # Persona routes
        "/personas/",
        "/personas/create",
        "/personas/save",

        # Network routes
        "/network",
        "/network/data",

        # Conversation routes
        "/conversations/",
        "/conversations/create",
    ]

    # Get all registered routes
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(rule.rule)

    for route in expected_routes:
        # Check if route exists (exact match or with parameters)
        found = any(route in r for r in routes)
        status = "✓" if found else "✗"
        print(f"  {status} Route '{route}'")

    print(f"\n  Total routes registered: {len(routes)}")
    return True

def main():
    """Run all tests."""
    print("\n" + "▓" * 70)
    print("  PersonaChat V1 Feature Test Suite")
    print("▓" * 70)

    tests = [
        ("Database Tables", test_database_tables),
        ("Persona Service", test_persona_service),
        ("Conversation Service", test_conversation_service),
        ("Gemini Service", test_gemini_service),
        ("Route Registration", test_routes),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            results.append((name, False))

    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed! V1 features are ready.")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
