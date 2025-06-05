#!/usr/bin/env python3
"""
Test Supabase Integration

This script tests the basic Supabase integration functionality including:
- Configuration loading
- Database connection
- Plugin initialization
- Basic operations
"""

# Standard library imports
from datetime import datetime

# Third-party imports
import pytest

# Local imports
from src.integrations import integration_registry
from src.models import EmailData, ProcessedEmail
from src.supabase_integration import (
    SupabaseConfig,
    SupabaseDatabaseInterface,
    SupabasePlugin,
)


@pytest.mark.asyncio
async def test_supabase_config():
    """Test Supabase configuration."""
    print("🔧 Testing Supabase Configuration...")

    try:
        config = SupabaseConfig()
        print("   ✅ Configuration loaded successfully")
        print(f"   📊 Supabase URL: {config.supabase_url[:30]}...")
        print(f"   🔑 API Key configured: {'Yes' if config.supabase_key else 'No'}")
        print(f"   🗄️ Tables configured: {len(config.TABLES)}")
        return True
    except Exception as e:
        print(f"   ❌ Configuration failed: {str(e)}")
        return False


@pytest.mark.asyncio
async def test_database_interface():
    """Test Supabase database interface."""
    print("\n🗄️ Testing Supabase Database Interface...")

    try:
        config = SupabaseConfig()
        db = SupabaseDatabaseInterface(config)

        # Test connection
        print("   🔌 Testing database connection...")
        await db.connect()
        print("   ✅ Database connection successful")

        # Test basic stats retrieval
        print("   📊 Testing stats retrieval...")
        stats = await db.get_stats()
        print(f"   ✅ Stats retrieved: {stats.total_processed} emails processed")

        # Clean up
        await db.disconnect()
        print("   🔌 Database disconnected")

        return True
    except Exception as e:
        print(f"   ❌ Database interface test failed: {str(e)}")
        return False


@pytest.mark.asyncio
async def test_plugin_integration():
    """Test Supabase plugin."""
    print("\n🔌 Testing Supabase Plugin...")

    try:
        config = SupabaseConfig()
        plugin = SupabasePlugin(config)

        # Test initialization
        print("   🚀 Testing plugin initialization...")
        initialized = await plugin.initialize()
        print(f"   ✅ Plugin initialized: {initialized}")

        # Get plugin metadata
        metadata = plugin.get_metadata()
        print(f"   📋 Plugin name: {metadata['name']}")
        print(f"   📋 Plugin version: {metadata['version']}")
        print(f"   📋 Capabilities: {len(metadata['capabilities'])}")

        # Test email processing (mock data)
        print("   📧 Testing email processing...")
        test_email_data = EmailData(
            message_id="test-123",
            from_email="test@example.com",
            to_emails=["user@example.com"],
            subject="Test Email",
            text_body="This is a test email for Supabase integration.",
            received_at=datetime.now(),
            headers={"message-id": "test-123"},
            attachments=[],
        )

        # Create ProcessedEmail from EmailData
        test_email = ProcessedEmail(id="test-processed-123", email_data=test_email_data)

        processed = await plugin.process_email(test_email)
        if processed:
            print(f"   ✅ Email processed successfully: ID {processed.id}")
            if hasattr(processed, "priority"):
                print(f"   📊 Priority: {processed.priority}")
            if hasattr(processed, "urgency_score"):
                print(f"   📊 Urgency Score: {processed.urgency_score}")
        else:
            print("   ⚠️ Email processing returned None (check configuration)")

        # Clean up
        await plugin.cleanup()
        print("   🧹 Plugin cleanup completed")

        return True
    except Exception as e:
        print(f"   ❌ Plugin test failed: {str(e)}")
        return False


@pytest.mark.asyncio
async def test_integration_registry():
    """Test integration with the registry."""
    print("\n📚 Testing Integration Registry...")

    try:
        # Use the imported integration_registry

        # Check if Supabase is registered
        supabase_db = integration_registry.get_database("supabase")
        if supabase_db:
            print("   ✅ Supabase database interface registered")
        else:
            print("   ⚠️ Supabase database interface not found in registry")

        # Check plugins
        plugins = integration_registry.plugin_manager.list_plugins()
        if "supabase" in plugins:
            print("   ✅ Supabase plugin registered")
        else:
            print("   ⚠️ Supabase plugin not found in registry")

        # List all integrations
        integrations = integration_registry.list_integrations()
        print(f"   📊 Available databases: {integrations['databases']}")
        print(f"   📊 Available plugins: {integrations['plugins']}")

        return True
    except Exception as e:
        print(f"   ❌ Integration registry test failed: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 Supabase Integration Test Suite")
    print("=" * 50)


#     test_results.append(await test_plugin_integration())
#     test_results.append(await test_integration_registry())
#
#     # Summary
#     print("\n" + "=" * 50)
#     print("📊 Test Results Summary")
#     print("=" * 50)
#
#     passed = sum(test_results)
#     total = len(test_results)
#
#     print(f"✅ Tests Passed: {passed}/{total}")
#     print(f"❌ Tests Failed: {total - passed}/{total}")
#
#     if passed == total:
#         print("🎉 All tests passed! Supabase integration is ready.")
#         return True
#     else:
#         print("⚠️  Some tests failed. Check configuration and dependencies.")
#         return False


# if __name__ == "__main__":
#     success = asyncio.run(main())
#     sys.exit(0 if success else 1)
