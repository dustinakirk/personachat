"""
Unit tests for SupabaseService helpers.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "supabase_service.py"
spec = importlib.util.spec_from_file_location("supabase_service_module", MODULE_PATH)
supabase_service_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = supabase_service_module
spec.loader.exec_module(supabase_service_module)

SupabaseService = supabase_service_module.SupabaseService

DUMMY_URL = "https://example.supabase.co"
DUMMY_KEY = "anon-test-key"


@patch.object(supabase_service_module, "create_client")
def test_get_authenticated_client_uses_user_token(mock_create_client):
    base_client = Mock()
    authed_client = Mock()
    authed_client.options.headers = {}
    authed_client.postgrest.auth = Mock()

    # First call for service init, second call for authenticated client
    mock_create_client.side_effect = [base_client, authed_client]

    service = SupabaseService(DUMMY_URL, DUMMY_KEY)

    result = service.get_authenticated_client("user-token-123")

    assert result is authed_client
    assert authed_client.options.headers["Authorization"] == "Bearer user-token-123"
    authed_client.postgrest.auth.assert_called_once_with("user-token-123")

    # Ensure we requested a client with custom options for the authed request
    _, kwargs = mock_create_client.call_args_list[1]
    options = kwargs.get("options")
    assert options is not None
    assert options.auto_refresh_token is False
    assert options.persist_session is False


@patch.object(supabase_service_module, "create_client")
def test_get_authenticated_client_requires_token(mock_create_client):
    mock_create_client.return_value = Mock()

    service = SupabaseService(DUMMY_URL, DUMMY_KEY)
    # Missing token should short-circuit without creating a new client
    assert service.get_authenticated_client("") is None
    assert mock_create_client.call_count == 1
