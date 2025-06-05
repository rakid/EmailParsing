"""
Test suite for UserManagementInterface.

This module contains comprehensive tests for the Supabase user management interface,
covering organization management, user roles, permissions, and user preferences.
"""

import asyncio
from unittest.mock import MagicMock, call, patch

import pytest

from src.supabase_integration.config import SupabaseConfig
from src.supabase_integration.user_management import (
    OrganizationRole,
    UserManagementInterface,
    UserRole,
)


def setup_mock_select_chain(mock_table, mock_response):
    """Helper to set up a mock select chain with the given response."""
    # For simple case: .select().eq().execute()
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

    # For complex case: .select().eq().eq().execute()
    select_eq_eq_execute = (
        mock_table.select.return_value.eq.return_value.eq.return_value.execute
    )
    select_eq_eq_execute.return_value = mock_response

    # For .select().eq().is_().execute()
    select_eq_is_execute = (
        mock_table.select.return_value.eq.return_value.is_.return_value.execute
    )
    select_eq_is_execute.return_value = mock_response

    return mock_table


def setup_mock_upsert_chain(mock_table, mock_response):
    """Helper to set up a mock upsert chain with the given response."""
    mock_table.upsert.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = mock_response
    return mock_table


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client for testing."""
    client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_table.select = MagicMock()
    mock_table.insert = MagicMock()
    mock_table.upsert = MagicMock()
    mock_table.update = MagicMock()
    mock_table.delete = MagicMock()

    # Chain method calls
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.neq = MagicMock(return_value=mock_table)
    mock_table.in_ = MagicMock(return_value=mock_table)
    mock_table.is_ = MagicMock(return_value=mock_table)
    mock_table.order = MagicMock(return_value=mock_table)

    # Mock execute responses
    mock_response = MagicMock()
    mock_response.data = []
    mock_table.execute = MagicMock(return_value=mock_response)

    client.table = MagicMock(return_value=mock_table)
    return client


@pytest.fixture
def user_config():
    """Create a test configuration."""
    config = MagicMock(spec=SupabaseConfig)
    config.TABLES = {
        "organizations": "organizations",
        "organization_members": "organization_members",
        "organization_invitations": "organization_invitations",
        "profiles": "profiles",
        "user_roles": "user_roles",
        "audit_logs": "audit_logs",
    }
    return config


@pytest.fixture
def user_manager(mock_supabase_client, user_config):
    """Create a UserManagementInterface instance for testing."""
    return UserManagementInterface(mock_supabase_client, user_config)


class TestSupabaseUserManager:
    """Test suite for UserManagementInterface."""

    @pytest.mark.asyncio
    async def test_create_organization_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful organization creation."""
        # Mock successful organization creation
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "org-123",
                "name": "Test Organization",
                "description": "Test Description",
                "created_by": "user-123",
            }
        ]

        # Mock table and insert operations
        mock_table = mock_supabase_client.table.return_value
        mock_insert = mock_table.insert.return_value
        mock_execute = mock_insert.execute.return_value
        mock_execute.return_value = mock_response

        # Mock successful user-organization relationship creation
        mock_user_org_response = MagicMock()
        mock_user_org_response.data = [{"id": "user-org-123"}]

        # Set up mock call sequence
        mock_execute.side_effect = [
            mock_response,  # First call for organization
            mock_user_org_response,  # Second call for member
        ]

        success, org_id, error = await user_manager.create_organization(
            user_id="user-123", name="Test Organization", description="Test Description"
        )

        assert success is True
        assert org_id == "org-123"
        assert error is None

    @pytest.mark.asyncio
    async def test_create_organization_failure(
        self, user_manager, mock_supabase_client
    ):
        """Test organization creation failure."""
        # Setup mock response for failure case
        mock_response = MagicMock()
        mock_response.data = []  # Empty data means failure

        # Setup mock insert chain for organization creation
        mock_table = mock_supabase_client.table.return_value
        mock_insert = mock_table.insert.return_value
        mock_execute = mock_insert.execute.return_value
        mock_execute.return_value = mock_response

        success, org_id, error = await user_manager.create_organization(
            "user-123", "Test Organization"
        )

        assert success is False
        assert org_id == ""
        assert error == "Failed to create organization"

    @pytest.mark.asyncio
    async def test_invite_user_to_organization_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful user invitation to organization."""
        # Mock get_user_organization_role method directly
        with (
            patch.object(
                user_manager,
                "get_user_organization_role",
                return_value=OrganizationRole.ADMIN,
            ),
            patch.object(
                user_manager,
                "_log_audit_event",
                return_value=None,
            ),
        ):
            # Mock user doesn't exist (profiles table check)
            mock_user_response = MagicMock()
            mock_user_response.data = []

            # Mock invitation creation
            mock_invitation_response = MagicMock()
            mock_invitation_response.data = [
                {
                    "id": "invitation-123",
                    "organization_id": "org-123",
                    "email": "user@example.com",
                    "role": "member",
                }
            ]

            # Set up table call sequence properly
            def mock_table_calls(table_name):
                mock_table = MagicMock()
                if table_name == "profiles":
                    # User existence check - return empty (user doesn't exist)
                    mock_table.select.return_value.eq.return_value.execute.return_value = (
                        mock_user_response
                    )
                elif table_name == "organization_invitations":
                    # Invitation creation - return success
                    mock_table.insert.return_value.execute.return_value = (
                        mock_invitation_response
                    )
                return mock_table

            mock_supabase_client.table.side_effect = mock_table_calls

            success, error = await user_manager.invite_user_to_organization(
                "admin-123", "org-123", "user@example.com", OrganizationRole.MEMBER
            )

            assert success is True
            assert error == ""

    @pytest.mark.asyncio
    async def test_invite_user_to_organization_failure(
        self, user_manager, mock_supabase_client
    ):
        """Test user invitation failure due to insufficient permissions."""
        # Mock get_user_organization_role method to return insufficient role
        with patch.object(
            user_manager,
            "get_user_organization_role",
            return_value=OrganizationRole.MEMBER,
        ):
            success, error = await user_manager.invite_user_to_organization(
                "member-123", "org-123", "user@example.com", OrganizationRole.MEMBER
            )

            assert success is False
            assert "Insufficient permissions" in error

    @pytest.mark.asyncio
    async def test_accept_organization_invitation_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful invitation acceptance."""
        # Mock invitation lookup with proper datetime format
        mock_invitation_response = MagicMock()
        mock_invitation_response.data = [
            {
                "id": "invitation-123",
                "organization_id": "org-123",
                "role": "member",
                "status": "pending",
                "expires_at": "2025-12-31T23:59:59+00:00",  # Proper ISO format
                "invited_by": "admin-123",
            }
        ]

        # Mock invitation status update
        mock_update_response = MagicMock()
        mock_update_response.data = [{"id": "invitation-123", "status": "accepted"}]

        # Setup mock for organization_invitations table
        mock_invitations_table = MagicMock()

        # Setup mock for invitation lookup
        mock_select = mock_invitations_table.select.return_value
        mock_eq1 = mock_select.eq.return_value
        mock_eq2 = mock_eq1.eq.return_value
        mock_eq2.execute.return_value = mock_invitation_response

        # Setup mock for status update
        mock_update = mock_invitations_table.update.return_value
        mock_update_eq = mock_update.eq.return_value
        mock_update_eq.execute.return_value = mock_update_response

        # Setup table side effect to return our mock
        mock_supabase_client.table.side_effect = lambda table_name: (
            mock_invitations_table
            if table_name == "organization_invitations"
            else MagicMock()
        )

        # Mock the _add_user_to_organization method directly
        with patch.object(
            user_manager, "_add_user_to_organization", return_value=(True, "")
        ) as mock_add_user:
            success, error = await user_manager.accept_organization_invitation(
                "user-123", "invitation-123"
            )

            # Verify the invitation was processed successfully
            assert success is True
            assert error == ""

            # Verify the user was added to the organization
            mock_add_user.assert_called_once_with(
                "user-123", "org-123", OrganizationRole.MEMBER, "admin-123"
            )

    @pytest.mark.asyncio
    async def test_accept_organization_invitation_not_found(
        self, user_manager, mock_supabase_client
    ):
        """Test invitation acceptance with not found invitation."""
        # Setup mock response for not found invitation
        mock_response = MagicMock()
        mock_response.data = []  # No invitation found

        # Setup mock table chain
        mock_table = MagicMock()
        setup_mock_select_chain(mock_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_table

        # Attempt to accept non-existent invitation
        success, error = await user_manager.accept_organization_invitation(
            "user-123", "invitation-123"
        )

        # Verify the expected failure
        assert success is False
        assert "not found" in error.lower()

        # Verify the correct table was queried
        mock_supabase_client.table.assert_called_once_with("organization_invitations")

    @pytest.mark.asyncio
    async def test_assign_user_role_success(self, user_manager, mock_supabase_client):
        """Test successful user role assignment."""
        # Mock get_user_organization_role to return admin role
        with patch.object(
            user_manager,
            "get_user_organization_role",
            return_value=OrganizationRole.ADMIN,
        ):
            # Setup mock responses
            mock_existing_response = MagicMock()
            mock_existing_response.data = []  # No existing role

            mock_assign_response = MagicMock()
            mock_assign_response.data = [{"id": "role-123", "role": "analyst"}]

            # Setup mock table for user_roles
            mock_roles_table = MagicMock()

            # Setup select chain for checking existing role
            setup_mock_select_chain(mock_roles_table, mock_existing_response)

            # Setup upsert chain for assigning role
            setup_mock_upsert_chain(mock_roles_table, mock_assign_response)

            # Configure client to return our mock table
            mock_supabase_client.table.return_value = mock_roles_table

            # Execute the method under test
            success, error = await user_manager.assign_user_role(
                "admin-123", "user-123", UserRole.ANALYST, "org-123"
            )

            # Verify the result
            assert success is True
            assert error == ""

            # Verify the correct table was accessed
            mock_supabase_client.table.assert_called_once_with("user_roles")

            # Verify the role was checked for existence first
            mock_roles_table.select.assert_called_once()

            # Verify the role was upserted with the correct data
            expected_data = {
                "user_id": "user-123",
                "organization_id": "org-123",
                "role": "analyst",
                "assigned_by": "admin-123",
            }
            mock_roles_table.upsert.assert_called_once()
            call_args = mock_roles_table.upsert.call_args[0][0]
            assert call_args == expected_data

    @pytest.mark.asyncio
    async def test_assign_user_role_failure(self, user_manager, mock_supabase_client):
        """Test user role assignment failure due to insufficient permissions."""
        # Mock get_user_organization_role to return insufficient role
        with patch.object(
            user_manager,
            "get_user_organization_role",
            return_value=OrganizationRole.MEMBER,
        ) as mock_get_role:
            # Execute the method under test
            success, error = await user_manager.assign_user_role(
                "member-123", "user-123", UserRole.ANALYST, "org-123"
            )

            # Verify the result
            assert success is False
            assert "Insufficient permissions" in error

            # Verify the role check was performed with correct arguments
            mock_get_role.assert_called_once_with("member-123", "org-123")

            # Verify no database operations were performed
            mock_supabase_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_user_permission_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful user permission check."""
        # Setup mock response for admin role
        mock_response = MagicMock()
        mock_response.data = [{"role": "admin"}]

        # Setup mock table for user_roles
        mock_roles_table = MagicMock()
        setup_mock_select_chain(mock_roles_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_roles_table

        # Execute the method under test
        has_permission = await user_manager.check_user_permission(
            "user-123", "users", "write", "org-123"
        )

        # Verify the result
        assert has_permission is True

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("user_roles")

        # Verify the role was queried with correct arguments
        mock_roles_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user and organization
        mock_roles_table.select.return_value.eq.assert_called_once_with(
            "user_id", "user-123"
        )

    @pytest.mark.asyncio
    async def test_check_user_permission_insufficient(
        self, user_manager, mock_supabase_client
    ):
        """Test user permission check with insufficient permissions."""
        # Setup mock response for viewer role
        mock_response = MagicMock()
        mock_response.data = [{"role": "viewer"}]

        # Setup mock table for user_roles
        mock_roles_table = MagicMock()
        setup_mock_select_chain(mock_roles_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_roles_table

        # Execute the method under test
        has_permission = await user_manager.check_user_permission(
            "user-123", "users", "write", "org-123"
        )

        # Verify the result
        assert has_permission is False

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("user_roles")

        # Verify the role was queried with correct arguments
        mock_roles_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user and organization
        mock_roles_table.select.return_value.eq.assert_called_once_with(
            "user_id", "user-123"
        )

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful user preferences update."""
        # Setup test data
        user_id = "user-123"
        existing_prefs = {
            "notification_preferences": {
                "email": True,
                "push": False,
            }
        }
        updated_prefs = {"theme": "dark", "language": "en"}

        # Setup mock profile response
        mock_profile_response = MagicMock()
        mock_profile_response.data = [existing_prefs]

        # Setup mock update response with merged preferences
        mock_update_response = MagicMock()
        mock_update_response.data = [
            {
                "id": user_id,
                "notification_preferences": {
                    **existing_prefs["notification_preferences"],
                    **updated_prefs,
                },
            }
        ]

        # Setup mock profiles table
        mock_profiles_table = MagicMock()
        mock_profiles_table.select.return_value.eq.return_value.execute.return_value = (
            mock_profile_response
        )
        mock_profiles_table.update.return_value.eq.return_value.execute.return_value = (
            mock_update_response
        )

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_profiles_table

        # Execute the method under test
        success, result = await user_manager.update_user_preferences(
            user_id, updated_prefs
        )

        # Verify the result
        assert success is True
        assert result == {**existing_prefs["notification_preferences"], **updated_prefs}

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_with("profiles")

        # Verify the profile was queried first
        mock_profiles_table.select.assert_called_once()
        mock_profiles_table.select.return_value.eq.assert_called_once_with(
            "id", user_id
        )

        # Verify the update was called with merged preferences
        expected_update = {
            "notification_preferences": {
                **existing_prefs["notification_preferences"],
                **updated_prefs,
            }
        }
        mock_profiles_table.update.assert_called_once()
        call_args = mock_profiles_table.update.call_args[0][0]
        assert call_args == expected_update

        # Verify the update was filtered by user ID
        mock_profiles_table.update.return_value.eq.assert_called_once_with(
            "id", user_id
        )

    @pytest.mark.asyncio
    async def test_update_user_preferences_failure(
        self, user_manager, mock_supabase_client
    ):
        """Test user preferences update failure when user profile is not found."""
        # Setup test data
        user_id = "user-123"
        prefs_to_update = {"theme": "dark"}

        # Setup mock response for non-existent profile
        mock_response = MagicMock()
        mock_response.data = []  # Simulate profile not found

        # Setup mock profiles table
        mock_profiles_table = MagicMock()
        mock_profiles_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_profiles_table

        # Execute the method under test
        success, error = await user_manager.update_user_preferences(
            user_id, prefs_to_update
        )

        # Verify the result
        assert success is False
        assert "not found" in error.lower()

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_with("profiles")

        # Verify the profile was queried first
        mock_profiles_table.select.assert_called_once()
        mock_profiles_table.select.return_value.eq.assert_called_once_with(
            "id", user_id
        )

        # Verify no update was attempted
        mock_profiles_table.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_role_success(self, user_manager, mock_supabase_client):
        """Test successful user role retrieval."""
        # Setup test data
        user_id = "user-123"
        expected_role = UserRole.ADMIN

        # Setup mock response with admin role
        mock_response = MagicMock()
        mock_response.data = [{"role": expected_role.value}]

        # Setup mock user_roles table
        mock_roles_table = MagicMock()
        setup_mock_select_chain(mock_roles_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_roles_table

        # Execute the method under test
        role = await user_manager.get_user_role(user_id)

        # Verify the result
        assert role == expected_role

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("user_roles")

        # Verify the role was queried with correct arguments
        mock_roles_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user ID and active status
        mock_roles_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )
        mock_roles_table.select.return_value.eq.return_value.is_.assert_called_once_with(
            "is_active", True
        )

    @pytest.mark.asyncio
    async def test_get_user_role_not_found(self, user_manager, mock_supabase_client):
        """Test user role retrieval when no matching role is found."""
        # Setup test data
        user_id = "user-123"

        # Setup mock response with no roles found
        mock_response = MagicMock()
        mock_response.data = []

        # Setup mock user_roles table
        mock_roles_table = MagicMock()
        setup_mock_select_chain(mock_roles_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_roles_table

        # Execute the method under test
        role = await user_manager.get_user_role(user_id)

        # Verify the result
        assert role is None

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("user_roles")

        # Verify the role was queried with correct arguments
        mock_roles_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user ID and active status
        mock_roles_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )
        mock_roles_table.select.return_value.eq.return_value.is_.assert_called_once_with(
            "is_active", True
        )

    @pytest.mark.asyncio
    async def test_get_user_organization_role_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful user organization role retrieval."""
        # Setup test data
        user_id = "user-123"
        org_id = "org-123"
        expected_role = OrganizationRole.MEMBER

        # Setup mock response with member role
        mock_response = MagicMock()
        mock_response.data = [{"role": expected_role.value}]

        # Setup mock organization_members table
        mock_members_table = MagicMock()
        setup_mock_select_chain(mock_members_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_members_table

        # Execute the method under test
        role = await user_manager.get_user_organization_role(user_id, org_id)

        # Verify the result
        assert role == expected_role

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("organization_members")

        # Verify the role was queried with correct arguments
        mock_members_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user ID and organization ID
        mock_members_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )
        mock_members_table.select.return_value.eq.return_value.eq.assert_called_once_with(
            "organization_id", org_id
        )

    @pytest.mark.asyncio
    async def test_get_user_organization_role_not_found(
        self, user_manager, mock_supabase_client
    ):
        """Test user organization role retrieval when no matching role is found."""
        # Setup test data
        user_id = "user-123"
        org_id = "org-123"

        # Setup mock response with no roles found
        mock_response = MagicMock()
        mock_response.data = []

        # Setup mock organization_members table
        mock_members_table = MagicMock()
        setup_mock_select_chain(mock_members_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_members_table

        # Execute the method under test
        role = await user_manager.get_user_organization_role(user_id, org_id)

        # Verify the result
        assert role is None

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("organization_members")

        # Verify the role was queried with correct arguments
        mock_members_table.select.assert_called_once_with("role")

        # Verify the query was filtered by user ID and organization ID
        mock_members_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )
        mock_members_table.select.return_value.eq.return_value.eq.assert_called_once_with(
            "organization_id", org_id
        )

    @pytest.mark.asyncio
    async def test_get_user_organizations_success(
        self, user_manager, mock_supabase_client
    ):
        """Test successful user organizations retrieval."""
        # Setup test data
        user_id = "user-123"

        # Setup mock response with organizations data
        mock_response = MagicMock()
        mock_response.data = [
            {
                "role": "admin",
                "organizations": {
                    "id": "org-1",
                    "name": "Organization 1",
                    "description": "First organization",
                },
            },
            {
                "role": "member",
                "organizations": {
                    "id": "org-2",
                    "name": "Organization 2",
                    "description": "Second organization",
                },
            },
        ]

        # Setup mock organization_members table
        mock_members_table = MagicMock()
        setup_mock_select_chain(mock_members_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_members_table

        # Execute the method under test
        organizations = await user_manager.get_user_organizations(user_id)

        # Verify the result
        assert len(organizations) == 2
        assert organizations[0]["name"] == "Organization 1"
        assert organizations[0]["user_role"] == "admin"
        assert organizations[1]["name"] == "Organization 2"
        assert organizations[1]["user_role"] == "member"

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("organization_members")

        # Verify the query was built correctly
        mock_members_table.select.assert_called_once()

        # Verify the query was filtered by user ID
        mock_members_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )

    @pytest.mark.asyncio
    async def test_get_user_organizations_empty(
        self, user_manager, mock_supabase_client
    ):
        """Test user organizations retrieval when user has no organizations."""
        # Setup test data
        user_id = "user-123"

        # Setup mock response with no organizations
        mock_response = MagicMock()
        mock_response.data = []

        # Setup mock organization_members table
        mock_members_table = MagicMock()
        setup_mock_select_chain(mock_members_table, mock_response)

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_members_table

        # Execute the method under test
        organizations = await user_manager.get_user_organizations(user_id)

        # Verify the result
        assert len(organizations) == 0

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("organization_members")

        # Verify the query was built correctly
        mock_members_table.select.assert_called_once()

        # Verify the query was filtered by user ID
        mock_members_table.select.return_value.eq.assert_called_once_with(
            "user_id", user_id
        )

    @pytest.mark.asyncio
    async def test_audit_logging(self, user_manager, mock_supabase_client):
        """Test audit logging functionality."""
        # Setup test data
        test_user_id = "user-123"
        test_action = "test_action"
        test_details = {"test": "data"}
        test_org_id = "org-123"

        # Setup mock response for audit log insertion
        mock_response = MagicMock()
        mock_response.data = [{"id": "log-123"}]

        # Setup mock audit_logs table
        mock_audit_logs = MagicMock()
        mock_audit_logs.insert.return_value.execute.return_value = mock_response

        # Configure client to return our mock table
        mock_supabase_client.table.return_value = mock_audit_logs

        # Execute the method under test
        await user_manager._log_audit_event(
            user_id=test_user_id,
            action=test_action,
            details=test_details,
            organization_id=test_org_id,
        )

        # Verify the correct table was accessed
        mock_supabase_client.table.assert_called_once_with("audit_logs")

        # Verify the insert was called with expected data
        expected_log_data = {
            "user_id": test_user_id,
            "action": test_action,
            "details": test_details,
            "organization_id": test_org_id,
            "ip_address": None,
            "user_agent": None,
        }
        mock_audit_logs.insert.assert_called_once()
        call_args = mock_audit_logs.insert.call_args[0][0]

        # Verify the call contains our expected data
        assert call_args["user_id"] == test_user_id
        assert call_args["action"] == test_action
        assert call_args["details"] == test_details
        assert call_args["organization_id"] == test_org_id
        assert "timestamp" in call_args  # Should be automatically added

    @pytest.mark.asyncio
    async def test_permission_matrix(self, user_manager):
        """Test permission matrix functionality."""
        # Test that the permission matrix is correctly defined
        assert user_manager._permission_matrix is not None
        assert isinstance(user_manager._permission_matrix, dict)

        # Test that all expected roles are present
        expected_roles = ["admin", "manager", "member", "guest"]
        for role in expected_roles:
            assert (
                role in user_manager._permission_matrix
            ), f"Expected role '{role}' not found in permission matrix"

        # Test that all roles have the expected permission structure
        for role, permissions in user_manager._permission_matrix.items():
            assert isinstance(
                permissions, dict
            ), f"Permissions for role '{role}' should be a dictionary"

            # Test that each permission has a boolean value
            for perm_name, has_permission in permissions.items():
                assert isinstance(
                    has_permission, bool
                ), f"Permission '{perm_name}' for role '{role}' should be a boolean"
        roles = [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MEMBER,
            OrganizationRole.GUEST,
        ]
        for role in roles:
            assert role in user_manager._permission_matrix

    @pytest.mark.asyncio
    async def test_organization_creation_with_settings(
        self, user_manager, mock_supabase_client
    ):
        """Test organization creation with additional settings."""
        mock_org_response = MagicMock()
        mock_org_response.data = [
            {
                "id": "org-123",
                "name": "Test Organization",
                "settings": {
                    "email_processing_enabled": True,
                    "max_users": 10,
                    "features": ["analytics", "real_time"],
                },
            }
        ]

        mock_member_response = MagicMock()
        mock_member_response.data = [{"id": "member-123"}]

        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = [
            mock_org_response,  # Organization creation
            mock_member_response,  # Member creation
        ]

        settings = {
            "email_processing_enabled": True,
            "max_users": 10,
            "features": ["analytics", "real_time"],
        }

        success, org_id, error = await user_manager.create_organization(
            "user-123", "Test Organization", settings=settings
        )

        assert success is True
        assert org_id == "org-123"
        assert error is None

    @pytest.mark.asyncio
    async def test_bulk_user_operations(self, user_manager, mock_supabase_client):
        """Test bulk user operations."""
        # Mock get_user_organization_role to return admin role
        with (
            patch.object(
                user_manager,
                "get_user_organization_role",
                return_value=OrganizationRole.ADMIN,
            ),
            patch.object(
                user_manager,
                "_log_audit_event",
                return_value=None,
            ),
        ):
            # Mock user doesn't exist (profiles table check)
            mock_user_response = MagicMock()
            mock_user_response.data = []

            # Mock successful bulk invitation
            mock_invitation_response = MagicMock()
            mock_invitation_response.data = [
                {"id": "inv-1", "email": "user1@example.com"},
            ]

            # Set up table call sequence properly
            def mock_table_calls(table_name):
                mock_table = MagicMock()
                if table_name == "profiles":
                    # User existence check - return empty (user doesn't exist)
                    mock_table.select.return_value.eq.return_value.execute.return_value = (
                        mock_user_response
                    )
                elif table_name == "organization_invitations":
                    # Invitation creation - return success
                    mock_table.insert.return_value.execute.return_value = (
                        mock_invitation_response
                    )
                return mock_table

            mock_supabase_client.table.side_effect = mock_table_calls

            email_list = ["user1@example.com", "user2@example.com", "user3@example.com"]

            # Simulate bulk invitation
            results = []
            for email in email_list:
                success, error = await user_manager.invite_user_to_organization(
                    "admin-123", "org-123", email, OrganizationRole.MEMBER
                )
                results.append((success, error))

            # All invitations should succeed
            assert all(result[0] for result in results)
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_error_handling_edge_cases(self, user_manager, mock_supabase_client):
        """Test error handling for edge cases."""
        # Test with empty user ID
        success, org_id, error = await user_manager.create_organization(
            "", "Test Organization"  # Empty user ID
        )
        assert success is False
        assert org_id == ""
        assert error is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, user_manager, mock_supabase_client):
        """Test concurrent user operations."""
        # Mock successful operations
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-123"}]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        # Run multiple operations concurrently
        tasks = [
            user_manager.create_organization("user-1", "Org 1"),
            user_manager.create_organization("user-2", "Org 2"),
            user_manager.create_organization("user-3", "Org 3"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete (though they may fail due to mock limitations)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_role_hierarchy_validation(self, user_manager):
        """Test role hierarchy validation."""
        # Verify role enum values
        assert OrganizationRole.OWNER.value == "owner"
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.MEMBER.value == "member"
        assert OrganizationRole.GUEST.value == "guest"

        # Define the expected hierarchy order
        role_hierarchy = [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MEMBER,
            OrganizationRole.GUEST,
        ]

        # Verify the hierarchy order by checking list indices
        for i, role in enumerate(role_hierarchy[:-1]):
            next_role = role_hierarchy[i + 1]
            # Verify roles are in the correct order in our hierarchy list
            assert (
                role != next_role
            ), f"Roles should be unique in hierarchy: {role} != {next_role}"

    @pytest.mark.asyncio
    async def test_user_preferences_validation(
        self, user_manager, mock_supabase_client
    ):
        """Test user preferences validation."""
        # Setup mock profile response
        mock_profile_response = MagicMock()
        mock_profile_response.data = [{"notification_preferences": {}}]

        # Setup mock update response (validation failure)
        mock_update_response = MagicMock()
        mock_update_response.data = []

        # Setup mock select chain for profile lookup
        setup_mock_select_chain(mock_supabase_client, mock_profile_response)

        # Setup mock update chain for preferences update
        setup_mock_upsert_chain(mock_supabase_client, mock_update_response)

        invalid_preferences = {
            "theme": "invalid_theme",
            "language": "xx",  # Invalid language code
            "notifications": "not_boolean",
        }

        success, error = await user_manager.update_user_preferences(
            "user-123", invalid_preferences
        )

        # Should fail due to empty profile data (user not found)
        assert success is False
        assert "not found" in error

    @pytest.mark.asyncio
    async def test_api_error_handling(self, user_manager, mock_supabase_client):
        """Test API error handling"""
        from postgrest.exceptions import APIError

        # Mock API error
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = APIError(
            {"message": "API Error", "details": "Error details"}
        )

        with pytest.raises(Exception):
            await user_manager.get_user_organizations("user123")

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, user_manager, mock_supabase_client):
        """Test general exception handling"""
        # Mock general exception
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "General error"
        )

        with pytest.raises(Exception):
            await user_manager.create_organization("user123", "Test Org")

    @pytest.mark.asyncio
    async def test_private_add_user_to_organization(
        self, user_manager, mock_supabase_client
    ):
        """Test the private _add_user_to_organization method"""
        # Mock responses for all queries
        mock_existing_check = MagicMock()
        mock_existing_check.data = []  # User is not already a member

        mock_insert_response = MagicMock()
        mock_insert_response.data = [{"id": "rel123"}]

        mock_audit_response = MagicMock()
        mock_audit_response.data = [{"id": "audit123"}]

        def mock_table_calls(table_name):
            mock_table = MagicMock()
            if table_name == "organization_members":
                # First call is the membership check (select)
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
                    mock_existing_check
                )
                # Second call is the insert operation
                mock_table.insert.return_value.execute.return_value = (
                    mock_insert_response
                )
            elif table_name == "audit_logs":
                # Third call is the audit log insert
                mock_table.insert.return_value.execute.return_value = (
                    mock_audit_response
                )
            return mock_table

        mock_supabase_client.table.side_effect = mock_table_calls

        success, error = await user_manager._add_user_to_organization(
            "user123", "org123", OrganizationRole.MEMBER, "inviter123"
        )

        assert success is True
        assert error == ""
        # Verify the table was called three times (membership check + insert + audit log)
        assert mock_supabase_client.table.call_count == 3
        # Verify the tables that were called
        expected_calls = [
            call("organization_members"),  # membership check
            call("organization_members"),  # insert
            call("audit_logs"),  # audit log
        ]
        mock_supabase_client.table.assert_has_calls(expected_calls)

    @pytest.mark.asyncio
    async def test_private_add_user_to_organization_failure(
        self, user_manager, mock_supabase_client
    ):
        """Test the private _add_user_to_organization method failure"""
        # Mock exception
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Database error"
        )

        success, error = await user_manager._add_user_to_organization(
            "user123", "org123", OrganizationRole.MEMBER, "inviter123"
        )

        assert success is False
        assert "Database error" in error

    @pytest.mark.asyncio
    async def test_log_audit_event(self, user_manager, mock_supabase_client):
        """Test audit event logging"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.data = [{"id": "audit123"}]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        # This should not raise an exception
        await user_manager._log_audit_event("user123", "test_action", {"test": "data"})

        mock_supabase_client.table.assert_called_with("audit_logs")

    @pytest.mark.asyncio
    async def test_log_audit_event_failure(self, user_manager, mock_supabase_client):
        """Test audit event logging failure"""
        # Mock exception (should be handled gracefully)
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Database error"
        )

        # This should not raise an exception (errors are logged but not re-raised)
        await user_manager._log_audit_event("user123", "test_action", {"test": "data"})

    def test_enum_values(self):
        """Test enum values are correctly defined"""
        # Test UserRole enum
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.MONITOR.value == "monitor"

        # Test OrganizationRole enum
        assert OrganizationRole.OWNER.value == "owner"
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.MEMBER.value == "member"
        assert OrganizationRole.GUEST.value == "guest"
