#!/usr/bin/env python3
"""
Comprehensive Tests for Real-time MCP Tools and Resources - Task #S007

Test file for the real-time capabilities added to the MCP Email Parsing Server,
including WebSocket integration, real-time subscriptions, and AI monitoring.
"""

# Standard library imports
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Third-party imports
import pytest

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Local imports
from src.mcp.types import TextContent
from src.models import EmailAnalysis, EmailData, UrgencyLevel
from src.server import (
    REALTIME_AVAILABLE,
    get_realtime_interface,
    handle_call_tool,
    handle_read_resource,
    reset_realtime_interface,
)
from src.storage import email_storage, stats


@pytest.fixture(autouse=True)
def reset_realtime_interface_fixture():
    """Reset real-time interface connections between tests."""
    reset_realtime_interface()  # Reset before each test
    yield
    # Reset after each test
    interface = get_realtime_interface()
    if interface and hasattr(interface, "reset_connections"):
        interface.reset_connections()
    reset_realtime_interface()  # Reset after each test


class TestRealtimeTools:
    """Test suite for real-time MCP tools."""

    @pytest.fixture
    def sample_email_data(self):
        """Sample email data for testing."""
        return EmailData(
            message_id="test-realtime-001",
            from_email="urgent@company.com",
            to_emails=["inbox@example.com"],
            subject="URGENT: Project deadline approaching",
            text_body=(
                "We need to finalize the quarterly report by tomorrow. "
                "Please review the attached documents and provide feedback "
                "by 5 PM today."
            ),
            html_body=None,
            received_at=datetime.now(),
        )

    @pytest.fixture
    def sample_analysis(self):
        """Sample analysis data for testing."""
        return EmailAnalysis(
            urgency_score=85,
            urgency_level=UrgencyLevel.HIGH,
            sentiment="urgent",
            confidence=0.92,
            keywords=["deadline", "urgent", "quarterly", "report"],
            action_items=["review documents", "provide feedback"],
            temporal_references=["tomorrow", "5 PM today"],
            tags=["urgent", "deadline", "work"],
            category="business",
        )

    @pytest.mark.asyncio
    async def test_subscribe_to_email_changes_basic(self):
        """Test basic email change subscription functionality."""
        arguments = {
            "user_id": "test_user_001",
            "filters": {
                "urgency_level": "high",
                "urgency_threshold": 70,
            },
        }

        result = await handle_call_tool("subscribe_to_email_changes", arguments)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "subscription_id" in response_data
        assert response_data["user_id"] == "test_user_001"
        assert response_data["filters"]["urgency_level"] == "high"

    @pytest.mark.asyncio
    async def test_subscribe_to_email_changes_with_sender_filter(self):
        """Test email subscription with sender filtering."""
        arguments = {
            "user_id": "test_user_002",
            "filters": {"sender": "@company.com", "urgency_threshold": 50},
        }

        result = await handle_call_tool("subscribe_to_email_changes", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["filters"]["sender"] == "@company.com"

    @pytest.mark.asyncio
    async def test_get_realtime_stats_live(self):
        """Test real-time statistics retrieval."""
        arguments = {
            "user_id": "test_user_001",
            "timeframe": "live",
            "include_ai_stats": True,
        }

        result = await handle_call_tool("get_realtime_stats", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        # Verify basic structure
        assert "user_id" in response_data
        assert "timeframe" in response_data
        assert "live_metrics" in response_data
        assert "ai_processing" in response_data

        # Verify metrics structure
        live_metrics = response_data["live_metrics"]
        assert "processing_rate" in live_metrics
        assert "active_connections" in live_metrics
        assert "queue_size" in live_metrics

    @pytest.mark.asyncio
    async def test_get_realtime_stats_hourly(self):
        """Test real-time statistics with hourly timeframe."""
        arguments = {
            "user_id": "test_user_001",
            "timeframe": "hour",
            "include_ai_stats": False,
        }

        result = await handle_call_tool("get_realtime_stats", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["timeframe"] == "hour"

    @pytest.mark.asyncio
    async def test_manage_user_subscriptions_list(self):
        """Test listing user subscriptions."""
        arguments = {"user_id": "test_user_001", "action": "list"}

        result = await handle_call_tool("manage_user_subscriptions", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["action"] == "list"
        assert "subscriptions" in response_data
        assert isinstance(response_data["subscriptions"], list)

    @pytest.mark.asyncio
    async def test_manage_user_subscriptions_create(self):
        """Test creating user subscription."""
        arguments = {
            "user_id": "test_user_001",
            "action": "create",
            "subscription_type": "urgent_emails",
            "preferences": {
                "enabled": True,
                "urgency_threshold": 80,
                "notification_methods": ["email", "websocket"],
            },
        }

        result = await handle_call_tool("manage_user_subscriptions", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["action"] == "create"
        assert response_data["subscription_type"] == "urgent_emails"
        assert "subscription_id" in response_data

    @pytest.mark.asyncio
    async def test_manage_user_subscriptions_update(self):
        """Test updating user subscription."""
        arguments = {
            "user_id": "test_user_001",
            "action": "update",
            "subscription_type": "urgent_emails",
            "preferences": {
                "urgency_threshold": 90,
                "notification_methods": ["websocket"],
            },
        }

        result = await handle_call_tool("manage_user_subscriptions", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["action"] == "update"
        assert response_data["subscription_type"] == "urgent_emails"
        assert response_data["status"] == "updated"

    @pytest.mark.asyncio
    async def test_manage_user_subscriptions_delete(self):
        """Test deleting user subscription."""
        arguments = {
            "user_id": "test_user_001",
            "action": "delete",
            "subscription_type": "urgent_emails",
        }

        result = await handle_call_tool("manage_user_subscriptions", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["action"] == "delete"
        assert response_data["subscription_type"] == "urgent_emails"

    @pytest.mark.asyncio
    async def test_monitor_ai_analysis_basic(self):
        """Test basic AI analysis monitoring."""
        arguments = {
            "user_id": "test_user_001",
            "analysis_types": ["urgency", "sentiment"],
        }

        result = await handle_call_tool("monitor_ai_analysis", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["user_id"] == "test_user_001"
        assert "analysis_types" in response_data
        assert "monitoring_data" in response_data

    @pytest.mark.asyncio
    async def test_monitor_ai_analysis_specific_email(self):
        """Test AI analysis monitoring for specific email."""
        arguments = {
            "user_id": "test_user_001",
            "email_id": "test-email-123",
            "analysis_types": ["urgency", "sentiment", "tasks"],
        }

        result = await handle_call_tool("monitor_ai_analysis", arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["email_id"] == "test-email-123"
        assert len(response_data["analysis_types"]) == 3


class TestRealtimeResources:
    """Test suite for real-time MCP resources."""

    def setup_method(self):
        """Setup method to ensure clean state for each test."""
        reset_realtime_interface()
        # Clear any storage state as well
        email_storage.clear()
        stats.total_processed = 0
        stats.total_errors = 0

    @pytest.mark.asyncio
    async def test_live_feed_resource(self):
        """Test live email feed resource."""
        result = await handle_read_resource("email://live-feed")

        assert result is not None
        feed_data = json.loads(result)

        if REALTIME_AVAILABLE:
            assert feed_data["status"] == "active"
            assert "live_notifications" in feed_data
            assert "active_subscriptions" in feed_data
            assert "feed_stats" in feed_data
            assert "realtime_info" in feed_data
        else:
            assert feed_data["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_realtime_stats_resource(self):
        """Test real-time statistics resource."""
        result = await handle_read_resource("email://realtime-stats")

        assert result is not None
        stats_data = json.loads(result)

        if REALTIME_AVAILABLE:
            assert stats_data["status"] == "active"
            assert "live_metrics" in stats_data
            assert "storage_stats" in stats_data
            assert "system_health" in stats_data
            assert "performance_metrics" in stats_data
        else:
            assert stats_data["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_user_subscriptions_resource(self):
        """Test user subscriptions resource."""
        result = await handle_read_resource("email://user-subscriptions")

        assert result is not None
        sub_data = json.loads(result)

        if REALTIME_AVAILABLE:
            assert sub_data["status"] == "active"
            assert "total_users" in sub_data
            assert "total_subscriptions" in sub_data
            assert "subscription_summary" in sub_data
            assert "user_subscriptions" in sub_data
            assert "subscription_types" in sub_data
        else:
            assert sub_data["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_ai_monitoring_resource(self):
        """Test AI monitoring resource."""
        result = await handle_read_resource("email://ai-monitoring")

        assert result is not None
        monitoring_data = json.loads(result)

        if REALTIME_AVAILABLE:
            assert monitoring_data["status"] == "active"
            assert "analysis_queue" in monitoring_data
            assert "performance_metrics" in monitoring_data
            assert "analysis_types" in monitoring_data
            assert "active_analyses" in monitoring_data
        else:
            assert monitoring_data["status"] == "unavailable"


class TestWebSocketIntegration:
    """Test suite for WebSocket integration functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connection_simulation(self):
        """Test WebSocket connection simulation."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None:
            pytest.skip("Real-time interface not available")

        # Test WebSocket connection
        user_id = "test_ws_user_001"
        if hasattr(interface, "connect_websocket"):
            connected = await interface.connect_websocket(user_id)
            assert connected is True
            assert user_id in interface.websocket_connections

            # Test disconnection
            disconnected = await interface.disconnect_websocket(user_id)
            assert disconnected is True
            assert user_id not in interface.websocket_connections

    @pytest.mark.asyncio
    async def test_real_time_update_sending(self):
        """Test real-time update sending through WebSocket."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None or not hasattr(interface, "send_realtime_update"):
            pytest.skip("Real-time interface not available or incomplete")

        user_id = "test_ws_user_002"
        if hasattr(interface, "connect_websocket"):
            await interface.connect_websocket(user_id)

        # Send update
        update_result = await interface.send_realtime_update(
            user_id, "new_email", {"email_id": "test-123", "urgency_score": 85}
        )

        assert update_result["sent"] is True
        assert update_result["user_id"] == user_id
        assert update_result["update_type"] == "new_email"

    @pytest.mark.asyncio
    async def test_subscription_with_websocket(self):
        """Test subscription creation with WebSocket integration."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None:
            pytest.skip("Real-time interface not available")

        user_id = "test_ws_user_003"

        # Create subscription (should auto-connect WebSocket)
        subscription = await interface.subscribe_to_email_changes(
            user_id, {"urgency_level": "high"}
        )

        # Check if websocket_connected field exists in response
        if "websocket_connected" in subscription:
            assert subscription["websocket_connected"] is True
        assert subscription["user_id"] == user_id


class TestErrorHandling:
    """Test suite for error handling in real-time functionality."""

    @pytest.mark.asyncio
    async def test_realtime_unavailable_handling(self):
        """Test handling when real-time functionality is unavailable."""
        # Temporarily disable real-time for testing
        with patch("src.server.REALTIME_AVAILABLE", False):
            arguments = {
                "user_id": "test_user_001",
                "filters": {"urgency_level": "high"},
            }

            result = await handle_call_tool("subscribe_to_email_changes", arguments)

            assert len(result) == 1
            assert "not available" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_subscription_action(self):
        """Test invalid subscription action handling."""
        arguments = {"user_id": "test_user_001", "action": "invalid_action"}

        result = await handle_call_tool("manage_user_subscriptions", arguments)

        assert len(result) == 1
        assert "unknown action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""
        # Missing user_id for subscription should be handled gracefully
        arguments = {"filters": {"urgency_level": "high"}}

        # This should either raise an exception or return an error message
        try:
            result = await handle_call_tool("subscribe_to_email_changes", arguments)
            # If it doesn't raise an exception, check for error message
            assert len(result) == 1
            assert (
                "error" in result[0].text.lower()
                or "required" in result[0].text.lower()
            )
        except (KeyError, TypeError, ValueError):
            # Expected behavior for missing required parameters
            pass


class TestPerformanceAndScaling:
    """Test suite for performance and scaling aspects."""

    @pytest.mark.asyncio
    async def test_multiple_subscriptions_performance(self):
        """Test performance with multiple subscriptions."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None:
            pytest.skip("Real-time interface not available")

        # Create multiple subscriptions
        user_ids = [f"perf_user_{i}" for i in range(10)]
        subscription_tasks = []

        for user_id in user_ids:
            task = interface.subscribe_to_email_changes(
                user_id, {"urgency_threshold": 70}
            )
            subscription_tasks.append(task)

        # Execute all subscriptions concurrently
        start_time = datetime.now()
        results = await asyncio.gather(*subscription_tasks)
        end_time = datetime.now()

        # Verify all subscriptions were successful
        assert len(results) == 10
        for result in results:
            assert "subscription_id" in result

        # Check performance (should complete within reasonable time)
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_websocket_connection_limits(self):
        """Test WebSocket connection handling under load."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None or not hasattr(interface, "connect_websocket"):
            pytest.skip("Real-time interface not available or incomplete")

        # Connect multiple users
        user_ids = [f"load_user_{i}" for i in range(20)]  # Reduced for testing
        connection_tasks = []

        for user_id in user_ids:
            task = interface.connect_websocket(user_id)
            connection_tasks.append(task)

        # Execute all connections
        results = await asyncio.gather(*connection_tasks)

        # Verify all connections were successful
        assert all(results)
        assert len(interface.websocket_connections) == 20


class TestDataIntegrity:
    """Test suite for data integrity in real-time operations."""

    @pytest.mark.asyncio
    async def test_subscription_data_persistence(self):
        """Test that subscription data persists correctly."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None:
            pytest.skip("Real-time interface not available")

        user_id = "data_integrity_user"

        # Create subscription
        subscription = await interface.subscribe_to_email_changes(
            user_id, {"urgency_level": "high", "urgency_threshold": 80}
        )

        subscription_id = subscription["subscription_id"]

        # Verify subscription exists in active subscriptions if available
        if hasattr(interface, "active_subscriptions"):
            assert subscription_id in interface.active_subscriptions

            # Verify subscription data integrity
            stored_sub = interface.active_subscriptions[subscription_id]
            assert stored_sub["user_id"] == user_id
            assert stored_sub["filters"]["urgency_level"] == "high"
            assert stored_sub["filters"]["urgency_threshold"] == 80

    @pytest.mark.asyncio
    async def test_analytics_data_consistency(self):
        """Test consistency of analytics data across calls."""
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time functionality not available")

        interface = get_realtime_interface()
        if interface is None:
            pytest.skip("Real-time interface not available")

        # Get analytics twice
        analytics1 = await interface.get_realtime_analytics("test_user", "live")
        analytics2 = await interface.get_realtime_analytics("test_user", "live")

        # Connection counts should be consistent (allowing for small variations)
        if "active_connections" in analytics1 and "active_connections" in analytics2:
            assert (
                abs(analytics1["active_connections"] - analytics2["active_connections"])
                <= 1
            )

        # Processing rates should be in expected range
        if "processing_rate" in analytics1:
            assert 0 <= analytics1["processing_rate"] <= 100
        if "processing_rate" in analytics2:
            assert 0 <= analytics2["processing_rate"] <= 100


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
