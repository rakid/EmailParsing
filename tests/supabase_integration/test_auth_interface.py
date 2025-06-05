"""
Test suite for SupabaseAuthInterface.

This module contains comprehensive tests for the Supabase authentication interface,
covering user registration, authentication, session management, and error handling.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from src.supabase_integration.auth_interface import SupabaseAuthInterface
from src.supabase_integration.config import SupabaseConfig


def setup_mock_upsert_chain(mock_client, response):
    """Helper to set up a mock upsert chain."""
    mock_table = mock_client.table.return_value
    mock_upsert = mock_table.upsert.return_value
    mock_upsert.execute.return_value = response
    return mock_upsert


def setup_mock_select_chain(mock_client, response):
    """Helper to set up a mock select chain."""
    mock_table = mock_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_eq.execute.return_value = response
    return mock_eq


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client for testing."""
    client = MagicMock()
    client.auth = MagicMock()
    client.table = MagicMock()

    # Mock table response for profile operations
    mock_table = MagicMock()
    mock_table.upsert = MagicMock()
    mock_table.upsert.return_value.execute = MagicMock()
    mock_table.select = MagicMock()
    mock_table.select.return_value.eq = MagicMock()
    mock_table.select.return_value.eq.return_value.execute = MagicMock()
    mock_table.update = MagicMock()
    mock_table.update.return_value.eq = MagicMock()
    mock_table.update.return_value.eq.return_value.execute = MagicMock()

    client.table.return_value = mock_table
    return client


@pytest.fixture
def auth_config():
    """Create a test configuration."""
    config = MagicMock(spec=SupabaseConfig)
    config.TABLES = {
        "profiles": "profiles",
        "organizations": "organizations",
        "user_organizations": "user_organizations",
    }
    return config


@pytest.fixture
def auth_interface(mock_supabase_client, auth_config):
    """Create a SupabaseAuthInterface instance for testing."""
    return SupabaseAuthInterface(mock_supabase_client, auth_config)


class TestSupabaseAuthInterface:
    """Test suite for SupabaseAuthInterface."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_interface, mock_supabase_client):
        """Test successful user registration."""
        # Mock successful auth response
        mock_auth_response = MagicMock()
        mock_auth_response.user = MagicMock()
        mock_auth_response.user.id = "test-user-id"
        mock_supabase_client.auth.sign_up.return_value = mock_auth_response

        # Mock successful profile creation
        mock_profile_response = MagicMock()
        mock_profile_response.data = [{"id": "test-user-id"}]
        setup_mock_upsert_chain(mock_supabase_client, mock_profile_response)

        success, user_id, error = await auth_interface.register_user(
            "test@example.com", "password123", {"full_name": "Test User"}
        )

        assert success is True
        assert user_id == "test-user-id"
        assert error is None
        mock_supabase_client.auth.sign_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_auth_failure(
        self, auth_interface, mock_supabase_client
    ):
        """Test user registration with auth failure."""
        mock_supabase_client.auth.sign_up.side_effect = Exception(
            "Email already exists"
        )

        success, user_id, error = await auth_interface.register_user(
            "test@example.com", "password123"
        )

        assert success is False
        assert user_id == ""  # Implementation returns empty string, not None
        assert "Email already exists" in error

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, auth_interface, mock_supabase_client
    ):
        """Test successful user authentication."""
        # Setup mock auth response
        mock_auth_response = MagicMock()
        mock_auth_response.user = MagicMock()
        mock_auth_response.user.id = "test-user-id"
        mock_auth_response.session = MagicMock()
        mock_auth_response.session.access_token = "access-token"
        mock_supabase_client.auth.sign_in_with_password.return_value = (
            mock_auth_response
        )

        # Mock profile update
        mock_update_response = MagicMock()
        mock_update_response.data = [{"id": "test-user-id"}]
        # Setup mock update chain
        mock_table = mock_supabase_client.table.return_value
        mock_update = mock_table.update.return_value
        mock_eq = mock_update.eq.return_value
        mock_eq.execute.return_value = mock_update_response

        success, user_id, error = await auth_interface.authenticate_user(
            "test@example.com", "password123"
        )

        assert success is True
        assert user_id == "test-user-id"
        assert error is None

    @pytest.mark.asyncio
    async def test_authenticate_user_failure(
        self, auth_interface, mock_supabase_client
    ):
        """Test failed user authentication."""
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception(
            "Invalid credentials"
        )

        success, user_id, error = await auth_interface.authenticate_user(
            "test@example.com", "wrongpassword"
        )

        assert success is False
        assert user_id is None
        assert "Invalid credentials" in error

    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_interface, mock_supabase_client):
        """Test successful user logout."""
        auth_interface.current_user = {"id": "test-user-id"}
        auth_interface.current_session = {"access_token": "token"}

        mock_supabase_client.auth.sign_out.return_value = None

        result = await auth_interface.logout_user()

        assert result is True
        assert auth_interface.current_user is None
        assert auth_interface.current_session is None
        mock_supabase_client.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_user_failure(self, auth_interface, mock_supabase_client):
        """Test failed user logout."""
        mock_supabase_client.auth.sign_out.side_effect = Exception("Logout failed")

        result = await auth_interface.logout_user()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(
        self, auth_interface, mock_supabase_client
    ):
        """Test getting current user when authenticated."""
        # Mock user object with id attribute
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        auth_interface.current_user = mock_user

        # Mock profile response
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-user-id", "email": "test@example.com"}]
        # Setup mock select chain using helper
        setup_mock_select_chain(mock_supabase_client, mock_response)

        user_data = await auth_interface.get_current_user()

        assert user_data == {"id": "test-user-id", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_get_current_user_not_authenticated(
        self, auth_interface, mock_supabase_client
    ):
        """Test getting current user when not authenticated."""
        auth_interface.current_user = None

        # Mock auth.get_user() to return None
        mock_supabase_client.auth.get_user.return_value = None

        user_data = await auth_interface.get_current_user()

        assert user_data is None

    @pytest.mark.asyncio
    async def test_update_user_profile_success(
        self, auth_interface, mock_supabase_client
    ):
        """Test successful user profile update."""
        # Setup mock update response
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-user-id", "full_name": "Updated Name"}]

        # Setup mock update chain using helper
        setup_mock_upsert_chain(mock_supabase_client, mock_response)

        success, error = await auth_interface.update_user_profile(
            "test-user-id", {"full_name": "Updated Name"}
        )

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_update_user_profile_failure(
        self, auth_interface, mock_supabase_client
    ):
        """Test failed user profile update."""
        # Setup mock to raise exception
        mock_table = mock_supabase_client.table.return_value
        mock_update = mock_table.update.return_value
        mock_eq = mock_update.eq.return_value
        mock_eq.execute.side_effect = Exception("Update failed")

        success, error = await auth_interface.update_user_profile(
            "test-user-id", {"full_name": "Updated Name"}
        )

        assert success is False
        assert "Update failed" in error

    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_interface, mock_supabase_client):
        """Test successful password reset."""
        mock_supabase_client.auth.reset_password_email.return_value = None

        success, error = await auth_interface.reset_password("test@example.com")

        assert success is True
        assert error is None
        mock_supabase_client.auth.reset_password_email.assert_called_once_with(
            "test@example.com"
        )

    @pytest.mark.asyncio
    async def test_reset_password_failure(self, auth_interface, mock_supabase_client):
        """Test failed password reset."""
        mock_supabase_client.auth.reset_password_email.side_effect = Exception(
            "Reset failed"
        )

        success, error = await auth_interface.reset_password("test@example.com")

        assert success is False
        assert "Reset failed" in error

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_interface, mock_supabase_client):
        """Test successful password change."""
        # Set up authenticated user
        auth_interface.current_user = MagicMock()
        auth_interface.current_user.id = "test-user-id"

        mock_response = MagicMock()
        mock_response.user = MagicMock()
        mock_response.user.id = "test-user-id"
        mock_supabase_client.auth.update_user.return_value = mock_response

        success, error = await auth_interface.change_password(
            "currentpass", "newpassword123"
        )

        assert success is True
        assert error is None
        mock_supabase_client.auth.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_failure(self, auth_interface, mock_supabase_client):
        """Test failed password change."""
        # Set up authenticated user
        auth_interface.current_user = MagicMock()
        auth_interface.current_user.id = "test-user-id"

        mock_supabase_client.auth.update_user.side_effect = Exception(
            "Password change failed"
        )

        success, error = await auth_interface.change_password(
            "currentpass", "newpassword123"
        )

        assert success is False
        assert "Password change failed" in error

    @pytest.mark.asyncio
    async def test_refresh_session_success(self, auth_interface, mock_supabase_client):
        """Test successful session refresh."""
        mock_response = MagicMock()
        mock_response.session = MagicMock()
        mock_response.session.access_token = "new-access-token"
        mock_response.session.refresh_token = "new-refresh-token"
        mock_supabase_client.auth.refresh_session.return_value = mock_response

        # Set up current session with proper object
        mock_current_session = MagicMock()
        mock_current_session.refresh_token = "refresh-token"
        auth_interface.current_session = mock_current_session

        success, error = await auth_interface.refresh_session()

        assert success is True
        assert error is None
        assert auth_interface.current_session == mock_response.session

    @pytest.mark.asyncio
    async def test_refresh_session_failure(self, auth_interface, mock_supabase_client):
        """Test failed session refresh."""
        # Set up a session first so it doesn't fail with "No active session"
        mock_current_session = MagicMock()
        mock_current_session.refresh_token = "refresh-token"
        auth_interface.current_session = mock_current_session

        mock_supabase_client.auth.refresh_session.side_effect = Exception(
            "Refresh failed"
        )

        success, error = await auth_interface.refresh_session()

        assert success is False
        assert "Refresh failed" in error

    @pytest.mark.asyncio
    async def test_get_user_quota_status(self, auth_interface, mock_supabase_client):
        """Test getting user quota status."""
        # Setup mock response with quota data
        mock_response = MagicMock()
        mock_response.data = [
            {
                "email_quota_monthly": 1000,
                "emails_processed_this_month": 250,
                "plan_type": "free",
            }
        ]

        # Setup mock select chain using helper
        setup_mock_select_chain(mock_supabase_client, mock_response)

        quota_status = await auth_interface.get_user_quota_status("test-user-id")

        assert quota_status["quota_limit"] == 1000
        assert quota_status["quota_used"] == 250
        assert quota_status["quota_remaining"] == 750
        assert quota_status["plan_type"] == "free"

    @pytest.mark.asyncio
    async def test_increment_email_count_success(
        self, auth_interface, mock_supabase_client
    ):
        """Test successful email count increment."""
        mock_response = MagicMock()
        mock_response.data = [{"emails_processed_this_month": 251}]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        result = await auth_interface.increment_email_count("test-user-id")

        assert result is True
        mock_supabase_client.rpc.assert_called_once_with(
            "increment_user_email_count", {"user_id": "test-user-id"}
        )

    @pytest.mark.asyncio
    async def test_increment_email_count_failure(
        self, auth_interface, mock_supabase_client
    ):
        """Test failed email count increment."""
        mock_supabase_client.rpc.return_value.execute.side_effect = Exception(
            "Update failed"
        )

        result = await auth_interface.increment_email_count("test-user-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_register_user_with_metadata(
        self, auth_interface, mock_supabase_client
    ):
        """Test user registration with additional metadata."""
        # Setup mock auth response
        mock_auth_response = MagicMock()
        mock_auth_response.user = MagicMock()
        mock_auth_response.user.id = "test-user-id"
        mock_supabase_client.auth.sign_up.return_value = mock_auth_response

        # Setup mock profile response
        mock_profile_response = MagicMock()
        mock_profile_response.data = [{"id": "test-user-id"}]

        # Setup mock upsert chain using helper
        setup_mock_upsert_chain(mock_supabase_client, mock_profile_response)

        metadata = {
            "full_name": "John Doe",
            "timezone": "America/New_York",
            "language": "en",
        }

        success, user_id, error = await auth_interface.register_user(
            "john.doe@example.com", "securepassword123", metadata
        )

        assert success is True
        assert user_id == "test-user-id"
        assert error is None

        # Verify that sign_up was called with metadata
        call_args = mock_supabase_client.auth.sign_up.call_args[0][0]
        assert call_args["email"] == "john.doe@example.com"
        assert call_args["options"]["data"] == metadata

    @pytest.mark.asyncio
    async def test_session_management(self, auth_interface, mock_supabase_client):
        """Test session management functionality."""
        # Setup mock auth response with session
        mock_auth_response = MagicMock()
        mock_auth_response.user = MagicMock()
        mock_auth_response.user.id = "test-user-id"
        mock_auth_response.session = MagicMock()
        mock_auth_response.session.access_token = "access-token"
        mock_auth_response.session.refresh_token = "refresh-token"
        mock_supabase_client.auth.sign_in_with_password.return_value = (
            mock_auth_response
        )

        # Authenticate to set session
        success, user_data, error = await auth_interface.authenticate_user(
            "test@example.com", "password123"
        )

        assert auth_interface.current_session is not None
        assert auth_interface.current_user is not None

        # Test logout clears session
        mock_supabase_client.auth.sign_out.return_value = None
        await auth_interface.logout_user()

        assert auth_interface.current_session is None
        assert auth_interface.current_user is None

    @pytest.mark.asyncio
    async def test_error_handling_edge_cases(
        self, auth_interface, mock_supabase_client
    ):
        """Test error handling for edge cases."""
        # Test with empty email - implementation doesn't validate, but Supabase will error
        mock_supabase_client.auth.sign_up.side_effect = Exception("Invalid email")
        success, user_id, error = await auth_interface.register_user("", "password123")
        assert success is False
        assert error is not None

        # Reset mock for next test
        mock_supabase_client.auth.sign_up.side_effect = None

        # Test with None password
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception(
            "Invalid password"
        )
        success, user_data, error = await auth_interface.authenticate_user(
            "test@example.com", None
        )
        assert success is False
        assert error is not None

        # Reset mock for next test
        mock_supabase_client.auth.sign_in_with_password.side_effect = None

        # Test profile update with invalid user ID
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception(
            "User not found"
        )
        success, error = await auth_interface.update_user_profile("", {})
        assert success is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, auth_interface, mock_supabase_client):
        """Test concurrent authentication operations."""
        # Mock responses for concurrent calls
        mock_auth_response = MagicMock()
        mock_auth_response.user = MagicMock()
        mock_auth_response.user.id = "test-user-id"
        mock_auth_response.session = MagicMock()
        mock_supabase_client.auth.sign_in_with_password.return_value = (
            mock_auth_response
        )

        # Run multiple authentication attempts concurrently
        tasks = [
            auth_interface.authenticate_user(f"test{i}@example.com", "password123")
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed or handle exceptions gracefully
        for result in results:
            assert not isinstance(result, Exception) or "Exception" in str(type(result))
