"""
Tests for the Supabase Plugin Integration

This module tests the SupabasePlugin class and its integration with the
email processing system.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)
from src.supabase_integration.config import SupabaseConfig
from src.supabase_integration.plugin import SupabasePlugin


class TestSupabasePlugin:
    """Test class for SupabasePlugin functionality"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock Supabase configuration"""
        config = MagicMock(spec=SupabaseConfig)
        config.supabase_url = "https://test.supabase.co"
        config.supabase_key = "test_key"
        config.is_configured.return_value = True
        config.TABLES = {
            "emails": "emails",
            "email_analysis": "email_analysis",
            "email_attachments": "email_attachments",
        }
        return config

    @pytest.fixture
    def sample_email_data(self):
        """Create sample email data for testing"""
        return EmailData(
            message_id="test@example.com",
            from_email="sender@example.com",
            to_emails=["recipient@example.com"],
            subject="Test Email",
            text_body="This is a test email",
            received_at=datetime.now(),
        )

    @pytest.fixture
    def sample_processed_email(self, sample_email_data):
        """Create sample processed email for testing"""
        analysis = EmailAnalysis(
            urgency_score=75,
            urgency_level=UrgencyLevel.HIGH,
            sentiment="neutral",
            confidence=0.8,
            keywords=["test"],
            action_items=["Review"],
            temporal_references=[],
            tags=["important"],
            category="business",
        )

        return ProcessedEmail(
            id="test-id",
            email_data=sample_email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
        )

    @pytest.fixture
    def plugin(self, mock_config):
        """Create a SupabasePlugin instance with mock config"""
        return SupabasePlugin(mock_config)

    def test_plugin_initialization(self, plugin):
        """Test basic plugin initialization"""
        assert plugin.get_name() == "supabase"
        assert plugin.get_version() == "1.0.0"
        assert plugin.enabled is True
        assert plugin._initialized is False

    def test_get_dependencies(self, plugin):
        """Test plugin dependencies"""
        deps = plugin.get_dependencies()
        assert "supabase>=2.0.0" in deps
        assert "aiohttp" in deps
        assert "asyncio" in deps

    def test_get_metadata(self, plugin):
        """Test plugin metadata"""
        metadata = plugin.get_metadata()
        assert metadata["name"] == "supabase"
        assert metadata["version"] == "1.0.0"
        assert "multi_user_storage" in metadata["capabilities"]
        assert "real_time_notifications" in metadata["capabilities"]

    @pytest.mark.asyncio
    async def test_initialize_success(self, plugin, mock_config):
        """Test successful plugin initialization"""
        with patch.object(
            plugin.database, "connect", new_callable=AsyncMock
        ) as mock_connect:
            with patch(
                "src.supabase_integration.plugin.SupabaseAuthInterface"
            ) as mock_auth:
                with patch(
                    "src.supabase_integration.plugin.SupabaseRealtimeInterface"
                ) as mock_realtime:
                    with patch(
                        "src.supabase_integration.plugin.UserManagementInterface"
                    ) as mock_user_mgmt:
                        plugin.database.client = MagicMock()

                        await plugin.initialize()

                        assert plugin._initialized is True
                        mock_connect.assert_called_once()
                        mock_auth.assert_called_once()
                        mock_realtime.assert_called_once()
                        mock_user_mgmt.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_config_override(self, plugin):
        """Test initialization with config override"""
        config_override = {
            "supabase_url": "https://override.supabase.co",
            "supabase_key": "override_key",
        }

        with patch.object(plugin.database, "connect", new_callable=AsyncMock):
            with patch.object(plugin.config, "supabase_url", "original_url"):
                plugin.database.client = MagicMock()

                await plugin.initialize(config_override)

                assert plugin.config.supabase_url == "https://override.supabase.co"
                assert plugin.config.supabase_key == "override_key"

    @pytest.mark.asyncio
    async def test_initialize_failure(self, plugin):
        """Test plugin initialization failure"""
        with patch.object(
            plugin.database, "connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await plugin.initialize()

            assert plugin._initialized is False

    @pytest.mark.asyncio
    async def test_process_email_not_initialized(self, plugin, sample_processed_email):
        """Test email processing when plugin not initialized"""
        result = await plugin.process_email(sample_processed_email)
        assert result == sample_processed_email

    @pytest.mark.asyncio
    async def test_process_email_disabled(self, plugin, sample_processed_email):
        """Test email processing when plugin is disabled"""
        plugin._initialized = True
        plugin.enabled = False

        result = await plugin.process_email(sample_processed_email)
        assert result == sample_processed_email

    @pytest.mark.asyncio
    async def test_process_email_success(self, plugin, sample_processed_email):
        """Test successful email processing"""
        plugin._initialized = True
        plugin.enabled = True

        with patch.object(
            plugin.database, "store_email", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = "stored-email-id"

            result = await plugin.process_email(sample_processed_email)

            mock_store.assert_called_once_with(sample_processed_email)
            assert "supabase" in result.analysis.tags

    @pytest.mark.asyncio
    async def test_authenticate_user(self, plugin):
        """Test user authentication"""
        plugin._initialized = True

        with patch.object(
            plugin.database, "authenticate_user", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = True

            result = await plugin.authenticate_user("test@example.com", "password")

            mock_auth.assert_called_once_with("test@example.com", "password")
            assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_user_not_initialized(self, plugin):
        """Test user authentication when not initialized"""
        with pytest.raises(RuntimeError, match="Plugin not initialized"):
            await plugin.authenticate_user("test@example.com", "password")

    @pytest.mark.asyncio
    async def test_register_user(self, plugin):
        """Test user registration"""
        plugin._initialized = True

        with patch.object(
            plugin.database, "register_user", new_callable=AsyncMock
        ) as mock_register:
            mock_register.return_value = "user123"

            user_id = await plugin.register_user("test@example.com", "password")

            mock_register.assert_called_once_with("test@example.com", "password", None)
            assert user_id == "user123"

    def test_get_current_user_id(self, plugin):
        """Test getting current user ID"""
        with patch.object(plugin.database, "get_current_user_id") as mock_get_user:
            mock_get_user.return_value = "user123"

            user_id = plugin.get_current_user_id()

            mock_get_user.assert_called_once()
            assert user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_email(self, plugin):
        """Test getting email by ID"""
        plugin._initialized = True

        with patch.object(
            plugin.database, "get_email", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await plugin.get_email("email123")

            mock_get.assert_called_once_with("email123")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_emails(self, plugin):
        """Test searching emails"""
        plugin._initialized = True

        with patch.object(
            plugin.database, "search_emails", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            results = await plugin.search_emails({"subject": "test"})

            mock_search.assert_called_once_with({"subject": "test"})
            assert results == []

    @pytest.mark.asyncio
    async def test_get_user_stats(self, plugin):
        """Test getting user statistics"""
        plugin._initialized = True

        mock_stats = MagicMock()
        mock_stats.total_processed = 10
        mock_stats.total_errors = 1
        mock_stats.avg_urgency_score = 75.0
        mock_stats.urgency_distribution = {"high": 5, "medium": 3, "low": 2}
        mock_stats.last_processed = datetime.now()
        mock_stats.processing_times = [1.5, 2.0, 1.8]

        with patch.object(
            plugin.database, "get_stats", new_callable=AsyncMock
        ) as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            stats = await plugin.get_user_stats()

            assert stats["total_processed"] == 10
            assert stats["total_errors"] == 1
            assert stats["avg_urgency_score"] == 75.0
            assert "urgency_distribution" in stats

    @pytest.mark.asyncio
    async def test_subscribe_to_email_changes(self, plugin):
        """Test subscribing to email changes"""
        plugin._initialized = True

        mock_channel = MagicMock()
        with patch.object(
            plugin.database, "subscribe_to_email_changes"
        ) as mock_subscribe:
            mock_subscribe.return_value = mock_channel

            # Define a no-op callback function
            def noop_callback(x):
                pass

            sub_id = await plugin.subscribe_to_email_changes(noop_callback)

            mock_subscribe.assert_called_once_with(noop_callback, None)
            assert sub_id in plugin._real_time_subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_from_email_changes(self, plugin):
        """Test unsubscribing from email changes"""
        mock_channel = MagicMock()
        plugin._real_time_subscriptions["test_sub"] = mock_channel

        result = await plugin.unsubscribe_from_email_changes("test_sub")

        assert result is True
        mock_channel.unsubscribe.assert_called_once()
        assert "test_sub" not in plugin._real_time_subscriptions

    @pytest.mark.asyncio
    async def test_cleanup(self, plugin):
        """Test plugin cleanup"""
        plugin._initialized = True

        # Add mock subscriptions
        mock_channel1 = MagicMock()
        mock_channel2 = MagicMock()
        plugin._real_time_subscriptions["sub1"] = mock_channel1
        plugin._real_time_subscriptions["sub2"] = mock_channel2

        with patch.object(
            plugin.database, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            await plugin.cleanup()

            mock_disconnect.assert_called_once()
            mock_channel1.unsubscribe.assert_called_once()
            mock_channel2.unsubscribe.assert_called_once()
            assert plugin._initialized is False
            assert len(plugin._real_time_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_get_realtime_stats(self, plugin):
        """Test getting realtime stats"""
        plugin._initialized = True

        mock_stats = MagicMock()
        mock_stats.total_processed = 10
        mock_stats.high_priority = 5
        mock_stats.average_urgency_score = 75.0
        mock_stats.success_rate = 95.0

        with patch.object(plugin.database, "set_user_context", new_callable=AsyncMock):
            with patch.object(
                plugin.database, "get_ai_enhanced_emails", new_callable=AsyncMock
            ) as mock_ai:
                with patch.object(
                    plugin.database,
                    "get_urgent_emails_realtime",
                    new_callable=AsyncMock,
                ) as mock_urgent:
                    with patch.object(
                        plugin.database, "get_stats", new_callable=AsyncMock
                    ) as mock_stats_call:
                        mock_ai.return_value = [1, 2, 3]
                        mock_urgent.return_value = [1]
                        mock_stats_call.return_value = mock_stats

                        stats = await plugin.get_realtime_stats("user123")

                        assert stats["user_id"] == "user123"
                        assert stats["ai_enhanced_emails"] == 3
                        assert stats["urgent_emails"] == 1
                        assert stats["total_processed"] == 10

    @pytest.mark.asyncio
    async def test_subscribe_to_email_updates(self, plugin):
        """Test subscribing to email updates"""
        plugin._initialized = True
        plugin.realtime = MagicMock()

        with patch.object(plugin.realtime, "connect", new_callable=AsyncMock):
            with patch.object(
                plugin.realtime, "subscribe_to_new_emails"
            ) as mock_subscribe:
                mock_subscribe.return_value = "sub123"

                # Define a no-op callback function
                def noop_callback(x):
                    pass

                sub_id = await plugin.subscribe_to_email_updates(
                    "user123", noop_callback
                )

                assert sub_id == "sub123"
                assert sub_id in plugin._real_time_subscriptions

    @pytest.mark.asyncio
    async def test_get_ai_enhanced_emails_by_user(self, plugin):
        """Test getting AI enhanced emails by user"""
        plugin._initialized = True

        with patch.object(plugin.database, "set_user_context", new_callable=AsyncMock):
            with patch.object(
                plugin.database, "get_ai_enhanced_emails", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = [{"email_id": "1"}, {"email_id": "2"}]

                emails = await plugin.get_ai_enhanced_emails_by_user(
                    "user123", limit=50
                )

                assert len(emails) == 2
                mock_get.assert_called_once_with(50)

    @pytest.mark.asyncio
    async def test_authenticate_user_session(self, plugin):
        """Test authenticating user session"""
        plugin._initialized = True
        plugin.auth = MagicMock()

        with patch.object(
            plugin.auth, "authenticate_user", new_callable=AsyncMock
        ) as mock_auth:
            with patch.object(plugin.auth, "get_current_session") as mock_session:
                mock_auth.return_value = (True, "user123", None)
                mock_session.return_value = {"token": "abc123"}

                success, user_id, session_info = await plugin.authenticate_user_session(
                    "test@example.com", "password"
                )

                assert success is True
                assert user_id == "user123"
                assert session_info == {"token": "abc123"}

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, plugin, sample_processed_email):
        """Test concurrent email processing"""
        plugin._initialized = True
        plugin.enabled = True

        with patch.object(
            plugin.database, "store_email", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = "stored-email-id"

            # Process multiple emails concurrently
            tasks = [plugin.process_email(sample_processed_email) for _ in range(5)]

            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all("supabase" in result.analysis.tags for result in results)
            assert mock_store.call_count == 5

    def test_plugin_configuration_validation(self, mock_config):
        """Test plugin configuration validation"""
        # Test with valid config
        plugin = SupabasePlugin(mock_config)
        assert plugin.config == mock_config

        # Test with None config (should create default)
        plugin_default = SupabasePlugin(None)
        assert plugin_default.config is not None

    @pytest.mark.asyncio
    async def test_error_handling_database_errors(self, plugin, sample_processed_email):
        """Test error handling for database errors"""
        plugin._initialized = True
        plugin.enabled = True

        with patch.object(
            plugin.database, "store_email", new_callable=AsyncMock
        ) as mock_store:
            mock_store.side_effect = Exception("Database error")

            # Should not raise exception but return original email
            result = await plugin.process_email(sample_processed_email)
            assert result == sample_processed_email


# =============================================================================
# COMPREHENSIVE PLUGIN ERROR HANDLING AND STATE MANAGEMENT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_initialization_with_connection_failure():
    """Test plugin initialization when database connection fails."""
    config = MagicMock(spec=SupabaseConfig)
    config.is_configured.return_value = True

    plugin = SupabasePlugin(config)

    with patch.object(
        plugin.database, "connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.side_effect = ConnectionError("Failed to connect to Supabase")

        with pytest.raises(ConnectionError, match="Failed to connect to Supabase"):
            await plugin.initialize()

        assert not plugin._initialized


@pytest.mark.asyncio
async def test_initialization_with_auth_failure():
    """Test plugin initialization when auth interface fails."""
    config = MagicMock(spec=SupabaseConfig)
    config.is_configured.return_value = True

    plugin = SupabasePlugin(config)

    with patch.object(plugin.database, "connect", new_callable=AsyncMock):
        plugin.database.client = MagicMock()  # Simulate successful database connection

        with patch("src.supabase_integration.plugin.SupabaseAuthInterface") as MockAuth:
            MockAuth.side_effect = Exception("Auth initialization failed")

            with pytest.raises(Exception, match="Auth initialization failed"):
                await plugin.initialize()


@pytest.mark.asyncio
async def test_initialization_with_config_override():
    """Test plugin initialization with config parameter override."""
    original_config = MagicMock(spec=SupabaseConfig)
    original_config.is_configured.return_value = True
    original_config.supabase_url = "https://original.supabase.co"
    original_config.supabase_key = "original-key"

    plugin = SupabasePlugin(original_config)

    # Override config during initialization
    override_config = {
        "supabase_url": "https://new.supabase.co",
        "supabase_key": "new-key",
    }

    with patch.object(plugin.database, "connect", new_callable=AsyncMock):
        plugin.database.client = MagicMock()

        with (
            patch("src.supabase_integration.plugin.SupabaseAuthInterface"),
            patch("src.supabase_integration.plugin.SupabaseRealtimeInterface"),
            patch("src.supabase_integration.plugin.UserManagementInterface"),
        ):

            await plugin.initialize(override_config)

            # Verify config was updated
            assert plugin.config.supabase_url == "https://new.supabase.co"
            assert plugin.config.supabase_key == "new-key"
            assert plugin._initialized


def test_plugin_metadata_comprehensive():
    """Test plugin metadata returns all expected information."""
    plugin = SupabasePlugin()
    metadata = plugin.get_metadata()

    # Basic metadata
    assert metadata["name"] == "supabase"
    assert metadata["version"] == "1.0.0"
    assert (
        metadata["description"]
        == "Supabase multi-user database and real-time integration"
    )
    assert metadata["enabled"] is True
    assert metadata["initialized"] is False

    # Capabilities
    expected_capabilities = [
        "multi_user_storage",
        "real_time_notifications",
        "row_level_security",
        "analytics_dashboard",
        "user_authentication",
        "cloud_storage",
        "real_time_sync",
        "user_management",
        "multi_tenancy",
        "rbac_support",
        "organization_management",
    ]

    assert "capabilities" in metadata
    for capability in expected_capabilities:
        assert capability in metadata["capabilities"]


def test_plugin_dependencies():
    """Test plugin dependencies are correctly specified."""
    plugin = SupabasePlugin()
    dependencies = plugin.get_dependencies()

    expected_deps = ["supabase>=2.0.0", "aiohttp", "asyncio"]
    assert dependencies == expected_deps


@pytest.mark.asyncio
async def test_process_email_when_disabled():
    """Test process_email when plugin is disabled."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.enabled = False

    # Create sample email
    email_data = EmailData(
        message_id="disabled@example.com",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        subject="Test Email",
        text_body="This is a test",
        received_at=datetime.now(),
        headers={},
        attachments=[],
    )
    email = ProcessedEmail(
        id="disabled-123",
        email_data=email_data,
        status=EmailStatus.RECEIVED,
        processed_at=None,
        analysis=None,
    )

    # Should return original email unchanged
    result = await plugin.process_email(email)
    assert result == email

    # Should not call database
    with patch.object(
        plugin.database, "store_email", new_callable=AsyncMock
    ) as mock_store:
        await plugin.process_email(email)
        mock_store.assert_not_called()


@pytest.mark.asyncio
async def test_process_email_not_initialized():
    """Test process_email when plugin is not initialized."""
    plugin = SupabasePlugin()
    plugin._initialized = False
    plugin.enabled = True

    email_data = EmailData(
        message_id="not-init@example.com",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        subject="Test Email",
        text_body="This is a test",
        received_at=datetime.now(),
        headers={},
        attachments=[],
    )
    email = ProcessedEmail(
        id="not-init-123",
        email_data=email_data,
        status=EmailStatus.RECEIVED,
        processed_at=None,
        analysis=None,
    )

    # Should return original email unchanged
    result = await plugin.process_email(email)
    assert result == email


# =============================================================================
# REAL-TIME SUBSCRIPTION MANAGEMENT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_subscribe_to_email_changes_success():
    """Test successful subscription to email changes."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.database = MagicMock()

    # Mock callback function
    def mock_callback(data):
        print(f"Received: {data}")

    mock_channel = MagicMock()
    plugin.database.subscribe_to_email_changes.return_value = mock_channel

    subscription_id = await plugin.subscribe_to_email_changes(
        mock_callback, {"urgency": "high"}
    )

    assert subscription_id.startswith("email_changes_")
    assert subscription_id in plugin._real_time_subscriptions
    assert plugin._real_time_subscriptions[subscription_id] == mock_channel

    # Verify the database method was called correctly
    plugin.database.subscribe_to_email_changes.assert_called_once_with(
        mock_callback, {"urgency": "high"}
    )


@pytest.mark.asyncio
async def test_subscribe_to_email_changes_not_initialized():
    """Test subscription when plugin is not initialized."""
    plugin = SupabasePlugin()
    plugin._initialized = False

    def mock_callback(data):
        pass

    with pytest.raises(RuntimeError, match="Plugin not initialized"):
        await plugin.subscribe_to_email_changes("user-123", mock_callback)


@pytest.mark.asyncio
async def test_subscribe_to_email_changes_realtime_unavailable():
    """Test subscription when plugin is not initialized."""
    plugin = SupabasePlugin()
    plugin._initialized = False

    def mock_callback(data):
        pass

    with pytest.raises(RuntimeError, match="Plugin not initialized"):
        await plugin.subscribe_to_email_changes(mock_callback)


@pytest.mark.asyncio
async def test_unsubscribe_from_email_changes_success():
    """Test successful unsubscription from email changes."""
    plugin = SupabasePlugin()

    # Set up existing subscription
    mock_channel = MagicMock()
    plugin._real_time_subscriptions["sub-123"] = mock_channel

    result = await plugin.unsubscribe_from_email_changes("sub-123")

    assert result is True
    assert "sub-123" not in plugin._real_time_subscriptions
    mock_channel.unsubscribe.assert_called_once()


@pytest.mark.asyncio
async def test_unsubscribe_from_email_changes_not_found():
    """Test unsubscription when subscription doesn't exist."""
    plugin = SupabasePlugin()

    result = await plugin.unsubscribe_from_email_changes("non-existent")

    assert result is False


@pytest.mark.asyncio
async def test_unsubscribe_from_email_changes_error():
    """Test unsubscription when unsubscribe operation fails."""
    plugin = SupabasePlugin()

    # Set up subscription that will fail to unsubscribe
    mock_channel = MagicMock()
    mock_channel.unsubscribe.side_effect = Exception("Unsubscribe failed")
    plugin._real_time_subscriptions["sub-123"] = mock_channel

    result = await plugin.unsubscribe_from_email_changes("sub-123")

    assert result is False
    # Subscription should still be removed even if unsubscribe failed
    assert "sub-123" not in plugin._real_time_subscriptions


# =============================================================================
# REAL-TIME STATS AND ANALYTICS TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_realtime_stats_success():
    """Test successful retrieval of real-time stats."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.database = MagicMock()
    plugin.auth = MagicMock()

    # Mock database responses
    mock_ai_emails = [{"id": "ai-1"}, {"id": "ai-2"}]
    mock_urgent_emails = [{"id": "urgent-1"}]
    mock_quota = {"used": 100, "limit": 1000}
    mock_stats = MagicMock()
    mock_stats.total_processed = 150
    mock_stats.total_errors = 5
    mock_stats.avg_urgency_score = 5.2

    with (
        patch.object(plugin.database, "set_user_context", new_callable=AsyncMock),
        patch.object(
            plugin.database, "get_ai_enhanced_emails", new_callable=AsyncMock
        ) as mock_ai,
        patch.object(
            plugin.database, "get_urgent_emails_realtime", new_callable=AsyncMock
        ) as mock_urgent,
        patch.object(
            plugin.database, "get_stats", new_callable=AsyncMock
        ) as mock_get_stats,
        patch.object(
            plugin.auth, "get_user_quota_status", new_callable=AsyncMock
        ) as mock_quota_status,
    ):

        mock_ai.return_value = mock_ai_emails
        mock_urgent.return_value = mock_urgent_emails
        mock_quota_status.return_value = mock_quota
        mock_get_stats.return_value = mock_stats

        result = await plugin.get_realtime_stats("user-123")

        assert result["user_id"] == "user-123"
        assert "timestamp" in result
        assert result["ai_enhanced_emails"] == 2
        assert result["urgent_emails"] == 1
        assert result["quota_status"] == mock_quota
        assert result["total_processed"] == 150
        assert result["total_errors"] == 5
        assert result["avg_urgency_score"] == 5.2


@pytest.mark.asyncio
async def test_get_realtime_stats_not_initialized():
    """Test get_realtime_stats when plugin is not initialized."""
    plugin = SupabasePlugin()
    plugin._initialized = False

    with pytest.raises(RuntimeError, match="Plugin not initialized"):
        await plugin.get_realtime_stats("user-123")


@pytest.mark.asyncio
async def test_get_realtime_stats_database_error():
    """Test get_realtime_stats when database operations fail."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.database = MagicMock()

    with patch.object(
        plugin.database, "set_user_context", new_callable=AsyncMock
    ) as mock_context:
        mock_context.side_effect = Exception("Database connection lost")

        result = await plugin.get_realtime_stats("user-123")

        assert "error" in result
        assert "Database connection lost" in result["error"]
        assert result["user_id"] == "user-123"


# =============================================================================
# EMAIL UPDATE SUBSCRIPTION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_subscribe_to_email_updates_success():
    """Test successful subscription to email updates."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.realtime = MagicMock()

    def mock_callback(data):
        print(f"Email update: {data}")

    filters = {"sender": "important@company.com"}

    with (
        patch.object(plugin.realtime, "connect", new_callable=AsyncMock),
        patch.object(plugin.realtime, "subscribe_to_new_emails") as mock_subscribe,
    ):

        mock_subscribe.return_value = "email-sub-456"

        subscription_id = await plugin.subscribe_to_email_updates(
            "user-456", mock_callback, filters
        )

        assert subscription_id == "email-sub-456"
        assert subscription_id in plugin._real_time_subscriptions

        # Verify subscription details
        sub_info = plugin._real_time_subscriptions[subscription_id]
        assert sub_info["user_id"] == "user-456"
        assert sub_info["type"] == "email_updates"
        assert "created_at" in sub_info

        # Verify realtime calls
        plugin.realtime.connect.assert_called_once_with("user-456")
        plugin.realtime.subscribe_to_new_emails.assert_called_once_with(
            mock_callback, filters
        )


@pytest.mark.asyncio
async def test_subscribe_to_email_updates_connection_failure():
    """Test subscription when realtime connection fails."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.realtime = MagicMock()

    def mock_callback(data):
        pass

    with patch.object(
        plugin.realtime, "connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await plugin.subscribe_to_email_updates("user-456", mock_callback)


# =============================================================================
# AI-ENHANCED EMAILS TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_ai_enhanced_emails_by_user_success():
    """Test successful retrieval of AI-enhanced emails by user."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.database = MagicMock()

    mock_emails = [
        {"id": "ai-email-1", "ai_enhanced": True},
        {"id": "ai-email-2", "ai_enhanced": True},
    ]

    with (
        patch.object(plugin.database, "set_user_context", new_callable=AsyncMock),
        patch.object(
            plugin.database, "get_ai_enhanced_emails", new_callable=AsyncMock
        ) as mock_get,
    ):

        mock_get.return_value = mock_emails

        result = await plugin.get_ai_enhanced_emails_by_user("user-789", limit=25)

        assert result == mock_emails
        plugin.database.set_user_context.assert_called_once_with("user-789")
        mock_get.assert_called_once_with(25)


@pytest.mark.asyncio
async def test_get_ai_enhanced_emails_by_user_database_error():
    """Test AI-enhanced emails retrieval when database fails."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.database = MagicMock()

    with patch.object(
        plugin.database, "set_user_context", new_callable=AsyncMock
    ) as mock_context:
        mock_context.side_effect = Exception("User context error")

        result = await plugin.get_ai_enhanced_emails_by_user("user-789")

        assert result == []


# =============================================================================
# AUTHENTICATION SESSION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_authenticate_user_session_success():
    """Test successful user authentication and session creation."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.auth = MagicMock()

    session_info = {
        "access_token": "token-123",
        "refresh_token": "refresh-456",
        "user": {"id": "user-123", "email": "test@example.com"},
    }

    with (
        patch.object(
            plugin.auth, "authenticate_user", new_callable=AsyncMock
        ) as mock_auth,
        patch.object(plugin.auth, "get_current_session") as mock_session,
    ):

        mock_auth.return_value = (True, "user-123", None)
        mock_session.return_value = session_info

        success, user_id, session = await plugin.authenticate_user_session(
            "test@example.com", "password123"
        )

        assert success is True
        assert user_id == "user-123"
        assert session == session_info

        mock_auth.assert_called_once_with("test@example.com", "password123")
        mock_session.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_user_session_failure():
    """Test user authentication failure."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.auth = MagicMock()

    with patch.object(
        plugin.auth, "authenticate_user", new_callable=AsyncMock
    ) as mock_auth:
        mock_auth.return_value = (False, None, "Invalid credentials")

        success, user_id, session = await plugin.authenticate_user_session(
            "wrong@example.com", "wrongpassword"
        )

        assert success is False
        assert user_id is None
        assert session == {"error": "Invalid credentials"}


@pytest.mark.asyncio
async def test_authenticate_user_session_auth_not_available():
    """Test authentication when auth interface is not available."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.auth = None

    with pytest.raises(RuntimeError, match="auth not available"):
        await plugin.authenticate_user_session("test@example.com", "password")


@pytest.mark.asyncio
async def test_authenticate_user_session_exception():
    """Test authentication when an exception occurs."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.auth = MagicMock()

    with patch.object(
        plugin.auth, "authenticate_user", new_callable=AsyncMock
    ) as mock_auth:
        mock_auth.side_effect = Exception("Auth service unavailable")

        success, user_id, session = await plugin.authenticate_user_session(
            "test@example.com", "password"
        )

        assert success is False
        assert user_id is None
        assert session == {"error": "Auth service unavailable"}


# =============================================================================
# PLUGIN STATE MANAGEMENT TESTS
# =============================================================================


def test_plugin_state_transitions():
    """Test plugin state transitions through initialization and operations."""
    plugin = SupabasePlugin()

    # Initial state
    assert plugin.name == "supabase"
    assert plugin.version == "1.0.0"
    assert plugin.enabled is True
    assert plugin._initialized is False
    assert plugin.auth is None
    assert plugin.realtime is None
    assert plugin.user_management is None
    assert len(plugin._real_time_subscriptions) == 0

    # State after setting initialized flag
    plugin._initialized = True
    metadata = plugin.get_metadata()
    assert metadata["initialized"] is True

    # State after adding subscriptions
    plugin._real_time_subscriptions["sub-1"] = {"test": "data"}
    assert len(plugin._real_time_subscriptions) == 1


def test_plugin_basic_interface_compliance():
    """Test that plugin implements basic PluginInterface methods correctly."""
    plugin = SupabasePlugin()

    # Test basic getters
    assert plugin.get_name() == "supabase"
    assert plugin.get_version() == "1.0.0"

    dependencies = plugin.get_dependencies()
    assert isinstance(dependencies, list)
    assert len(dependencies) > 0

    metadata = plugin.get_metadata()
    assert isinstance(metadata, dict)
    assert "name" in metadata
    assert "version" in metadata
    assert "capabilities" in metadata


# =============================================================================
# CONCURRENT OPERATIONS TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_concurrent_email_processing():
    """Test concurrent email processing operations."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.enabled = True
    plugin.database = MagicMock()

    # Create multiple sample emails
    emails = []
    for i in range(5):
        email_data = EmailData(
            message_id=f"concurrent-{i}@example.com",
            from_email="sender@example.com",
            to_emails=["recipient@example.com"],
            subject=f"Concurrent Email {i}",
            text_body=f"Test email {i}",
            received_at=datetime.now(),
            headers={},
            attachments=[],
        )
        email = ProcessedEmail(
            id=f"concurrent-{i}",
            email_data=email_data,
            status=EmailStatus.RECEIVED,
            processed_at=None,
            analysis=None,
        )
        emails.append(email)

    with patch.object(
        plugin.database, "store_email", new_callable=AsyncMock
    ) as mock_store:
        mock_store.return_value = "stored-id"

        # Process emails concurrently
        tasks = [plugin.process_email(email) for email in emails]
        results = await asyncio.gather(*tasks)

        # Verify all emails were processed
        assert len(results) == 5
        assert mock_store.call_count == 5

        # Verify all results have Supabase tags
        for result in results:
            assert result.analysis is not None
            assert "supabase" in result.analysis.tags


@pytest.mark.asyncio
async def test_concurrent_subscription_operations():
    """Test concurrent subscription operations."""
    plugin = SupabasePlugin()
    plugin._initialized = True
    plugin.realtime = MagicMock()

    def mock_callback(data):
        pass

    with (
        patch.object(plugin.realtime, "connect", new_callable=AsyncMock),
        patch.object(plugin.realtime, "subscribe_to_new_emails") as mock_subscribe,
    ):

        # Mock different subscription IDs
        mock_subscribe.side_effect = [f"sub-{i}" for i in range(3)]

        # Create multiple subscriptions concurrently using email_updates
        tasks = [
            plugin.subscribe_to_email_updates(f"user-{i}", mock_callback)
            for i in range(3)
        ]

        subscription_ids = await asyncio.gather(*tasks)

        # Verify all subscriptions were created
        assert len(subscription_ids) == 3
        assert len(plugin._real_time_subscriptions) == 3

        # For email_updates subscriptions, manually clean up since unsubscribe_from_email_changes
        # expects channel objects, but email_updates stores metadata dictionaries
        for sub_id in subscription_ids:
            if sub_id in plugin._real_time_subscriptions:
                plugin._real_time_subscriptions.pop(sub_id)

        # Verify cleanup worked
        assert len(plugin._real_time_subscriptions) == 0
