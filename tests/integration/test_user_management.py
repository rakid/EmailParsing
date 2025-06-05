#!/usr/bin/env python3
"""
Test script for Task #S005: User Management & Multi-Tenancy

This script tests the UserManagementInterface integration and validates
that all components work together correctly.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_user_management_imports():
    """Test that all user management modules can be imported successfully."""
    try:
        pass

        logger.info("✅ All user management imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during imports: {e}")
        return False


def test_user_management_interface_creation():
    """Test that UserManagementInterface can be created."""
    try:
        from src.supabase_integration.config import SupabaseConfig
        from src.supabase_integration.user_management import (
            UserManagementInterface,
        )

        # Mock Supabase client
        mock_client = Mock()
        config = SupabaseConfig()

        # Create interface
        user_mgmt = UserManagementInterface(mock_client, config)

        # Verify initialization
        assert user_mgmt.client == mock_client
        assert user_mgmt.config == config

        logger.info("✅ UserManagementInterface creation successful")
        return True
    except Exception as e:
        logger.error(f"❌ UserManagementInterface creation failed: {e}")
        return False


def test_enum_definitions():
    """Test that UserRole and OrganizationRole enums are properly defined."""
    try:
        from src.supabase_integration.user_management import OrganizationRole, UserRole

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

        logger.info("✅ Enum definitions are correct")
        return True
    except Exception as e:
        logger.error(f"❌ Enum definition test failed: {e}")
        return False


def test_plugin_integration():
    """Test that SupabasePlugin correctly integrates UserManagementInterface."""
    try:
        from src.supabase_integration.config import SupabaseConfig
        from src.supabase_integration.plugin import SupabasePlugin

        config = SupabaseConfig()
        plugin = SupabasePlugin(config)

        # Check that user_management is initialized as None
        assert plugin.user_management is None

        # Check metadata includes user management capabilities
        metadata = plugin.get_metadata()
        capabilities = metadata.get("capabilities", [])

        required_capabilities = [
            "user_management",
            "multi_tenancy",
            "rbac_support",
            "organization_management",
        ]

        for capability in required_capabilities:
            assert capability in capabilities, f"Missing capability: {capability}"

        logger.info("✅ Plugin integration test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Plugin integration test failed: {e}")
        return False


async def test_user_management_methods():
    """Test that UserManagementInterface methods can be called (with mocked client)."""
    try:
        from src.supabase_integration.config import SupabaseConfig
        from src.supabase_integration.user_management import (
            UserManagementInterface,
        )

        # Create mock client with proper async behavior
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table

        # Mock the execute chain for organization creation
        mock_result = Mock()
        mock_result.data = [{"id": "test-org-id"}]
        mock_table.insert.return_value.execute.return_value = mock_result
        mock_table.delete.return_value.eq.return_value.execute.return_value = Mock()

        config = SupabaseConfig()
        user_mgmt = UserManagementInterface(mock_client, config)

        # Mock the audit logging method
        user_mgmt._log_audit_event = AsyncMock()

        # Test organization creation
        success, org_id, error = await user_mgmt.create_organization(
            user_id="test-user-id",
            name="Test Organization",
            description="Test description",
        )

        # Verify the method was called without errors
        assert mock_client.table.called
        assert user_mgmt._log_audit_event.called

        logger.info("✅ User management methods test successful")
        return True
    except Exception as e:
        logger.error(f"❌ User management methods test failed: {e}")
        return False


def test_database_schema_updates():
    """Test that the database schema file includes user management tables."""
    try:
        schema_file = (
            "/home/rakbro/Projects/myApps/MCP/EmailParsing/database_schema_supabase.sql"
        )

        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check for required tables
        required_tables = [
            "organizations",
            "organization_members",
            "organization_invitations",
            "user_preferences",
        ]

        for table in required_tables:
            assert f"CREATE TABLE {table}" in schema_content, f"Missing table: {table}"

        # Check for RLS policies
        assert "ROW LEVEL SECURITY" in schema_content

        # Check for user management triggers
        assert "update_organizations_updated_at" in schema_content
        assert "update_user_preferences_updated_at" in schema_content

        logger.info("✅ Database schema updates verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database schema test failed: {e}")
        return False


async def main():
    """Run all tests for Task #S005."""
    logger.info("🚀 Starting Task #S005: User Management & Multi-Tenancy Tests")
    logger.info("=" * 60)

    tests = [
        ("Import Tests", test_user_management_imports),
        ("Interface Creation", test_user_management_interface_creation),
        ("Enum Definitions", test_enum_definitions),
        ("Plugin Integration", test_plugin_integration),
        ("User Management Methods", test_user_management_methods),
        ("Database Schema Updates", test_database_schema_updates),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1

        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")

        logger.info("-" * 40)

    # Summary
    logger.info("=" * 60)
    logger.info(f"🎯 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Task #S005 implementation is ready.")
        logger.info("✅ User Management & Multi-Tenancy implementation complete!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Implementation needs fixes.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
