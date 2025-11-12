#!/usr/bin/env python3
"""
Test script to verify persona creation with RLS authentication
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

from app.services.supabase_service import SupabaseService
from app.services.persona_service import PersonaService
from app.models import PersonaEnrichment

def test_persona_creation():
    """Test persona creation with authenticated client"""

    print("=" * 60)
    print("Testing Persona Creation with RLS Authentication")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("❌ ERROR: Please set SUPABASE_URL and SUPABASE_ANON_KEY in your environment.")
        return False

    # Initialize services
    supabase_service = SupabaseService(SUPABASE_URL, SUPABASE_ANON_KEY)
    persona_service = PersonaService(supabase_service._client, supabase_service)

    print("\n1. Testing Supabase configuration...")
    if not supabase_service.is_configured:
        print("❌ ERROR: Supabase is not configured!")
        print("   Please set SUPABASE_URL and SUPABASE_ANON_KEY")
        return False
    print("✅ Supabase is configured")

    # Get credentials for test
    test_email = input("\n2. Enter your test account email: ").strip()
    test_password = input("   Enter your test account password: ").strip()

    if not test_email or not test_password:
        print("❌ ERROR: Email and password required")
        return False

    # Login
    print("\n3. Logging in...")
    login_result = supabase_service.login_user(test_email, test_password)

    if not login_result.success:
        print(f"❌ Login failed: {login_result.error}")
        return False

    user_id = login_result.data.get("id")
    access_token = login_result.data.get("access_token")
    print(f"✅ Logged in successfully")
    print(f"   User ID: {user_id}")
    print(f"   Token: {access_token[:20]}..." if access_token else "   Token: None")

    # Test 1: Create persona WITHOUT access_token (should fail with RLS)
    print("\n4. Test 1: Creating persona WITHOUT access_token (should fail)...")
    test_enrichment = PersonaEnrichment(
        name="Test Persona No Token",
        role="Test Role",
        company="Test Company",
        goals=["Test goal"],
        pains=["Test pain"],
        tags=["test"]
    )

    result_no_token = persona_service.create_persona(user_id, test_enrichment, None, None)

    if not result_no_token.success:
        print(f"✅ Expected failure occurred: {result_no_token.error}")
        if isinstance(result_no_token.error, dict):
            error_code = result_no_token.error.get('code')
            print(f"   Error code: {error_code}")
            if error_code == '42501':
                print("   ✓ Correct RLS policy error code")
    else:
        print("❌ UNEXPECTED: Persona created without token (RLS should have blocked this)")
        return False

    # Test 2: Create persona WITH access_token (should succeed)
    print("\n5. Test 2: Creating persona WITH access_token (should succeed)...")
    test_enrichment2 = PersonaEnrichment(
        name="Test Persona With Token",
        role="Test Role",
        company="Test Company",
        goals=["Test goal"],
        pains=["Test pain"],
        tags=["test"]
    )

    result_with_token = persona_service.create_persona(user_id, test_enrichment2, None, access_token)

    if result_with_token.success:
        persona_id = result_with_token.data.get("id")
        print(f"✅ Persona created successfully!")
        print(f"   Persona ID: {persona_id}")
        print(f"   Name: {test_enrichment2.name}")

        # Clean up - delete test persona
        print("\n6. Cleaning up test persona...")
        delete_result = persona_service.delete_persona(persona_id)
        if delete_result.success:
            print("✅ Test persona deleted successfully")
        else:
            print(f"⚠️  Could not delete test persona: {delete_result.error}")
            print(f"   You may need to manually delete persona {persona_id}")

        return True
    else:
        print(f"❌ Persona creation failed: {result_with_token.error}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PersonaChat - RLS Authentication Test")
    print("=" * 60)

    try:
        success = test_persona_creation()
        print("\n" + "=" * 60)
        if success:
            print("✅ ALL TESTS PASSED!")
            print("\nThe RLS fix is working correctly:")
            print("  - Personas cannot be created without authentication")
            print("  - Personas can be created with valid access_token")
        else:
            print("❌ TESTS FAILED")
            print("\nThere may still be issues with RLS authentication.")
        print("=" * 60 + "\n")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
