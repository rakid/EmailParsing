"""
Supabase Real-time Interface

This module provides real-time capabilities for the Supabase integration,
including subscriptions to data changes, live updates, and real-time
notifications for the email processing system.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from supabase import Client

from .config import SupabaseConfig

logger = logging.getLogger(__name__)


class SupabaseRealtimeInterface:
    """
    Supabase real-time interface for live data updates.

    Features:
    - Real-time email processing notifications
    - Live dashboard updates
    - Task status changes
    - User activity monitoring
    - Subscription management
    """

    def __init__(self, client: Client, config: SupabaseConfig):
        """
        Initialize real-time interface.

        Args:
            client: Supabase client instance
            config: Supabase configuration
        """
        self.client = client
        self.config = config
        self.subscriptions: Dict[str, Any] = {}
        self.channels: Dict[str, Any] = {}
        self.current_user_id: Optional[str] = None
        self._is_connected = False

    async def connect(self, user_id: str) -> bool:
        """
        Connect to real-time services.

        Args:
            user_id: Current user ID for filtering

        Returns:
            bool: Connection success status
        """
        try:
            self.current_user_id = user_id
            self._is_connected = True
            logger.info(f"Real-time interface connected for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect real-time interface: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from real-time services and cleanup subscriptions."""
        try:
            # Unsubscribe from all channels
            for channel_name, channel in self.channels.items():
                try:
                    channel.unsubscribe()
                    logger.info(f"Unsubscribed from channel: {channel_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to unsubscribe from {channel_name}: {str(e)}"
                    )

            self.subscriptions.clear()
            self.channels.clear()
            self.current_user_id = None
            self._is_connected = False
            logger.info("Real-time interface disconnected")
        except Exception as e:
            logger.error(f"Error during real-time disconnect: {str(e)}")

    def subscribe_to_new_emails(
        self,
        callback: Callable[[Dict[str, Any]], None],
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Subscribe to new email notifications.

        Args:
            callback: Function to call when new emails arrive
            filters: Optional filters for subscription

        Returns:
            Subscription ID
        """
        if not self._is_connected:
            raise RuntimeError("Real-time interface not connected")

        channel_name = f"new_emails_{self.current_user_id}"

        try:
            # Create channel for new emails
            channel = self.client.channel(channel_name)

            # Configure subscription filter
            table_filter = f"user_id=eq.{self.current_user_id}"
            if filters:
                if "urgency_level" in filters:
                    table_filter += f",urgency_level=eq.{filters['urgency_level']}"
                if "sender" in filters:
                    table_filter += f",from_email=ilike.%{filters['sender']}%"

            # Subscribe to INSERT events on emails table
            channel.on(
                "postgres_changes",
                {
                    "event": "INSERT",
                    "schema": "public",
                    "table": self.config.TABLES["emails"],
                    "filter": table_filter,
                },
                self._wrap_callback(callback, "new_email"),
            )

            channel.subscribe()
            self.channels[channel_name] = channel

            logger.info(f"Subscribed to new emails for user {self.current_user_id}")
            return channel_name

        except Exception as e:
            logger.error(f"Failed to subscribe to new emails: {str(e)}")
            raise

    def subscribe_to_urgent_emails(
        self, callback: Callable[[Dict[str, Any]], None], urgency_threshold: int = 70
    ) -> str:
        """
        Subscribe to urgent email notifications.

        Args:
            callback: Function to call when urgent emails arrive
            urgency_threshold: Minimum urgency score (0-100)

        Returns:
            Subscription ID
        """
        if not self._is_connected:
            raise RuntimeError("Real-time interface not connected")

        channel_name = f"urgent_emails_{self.current_user_id}"

        try:
            channel = self.client.channel(channel_name)

            # Filter for urgent emails
            table_filter = (
                f"user_id=eq.{self.current_user_id},"
                f"urgency_score=gte.{urgency_threshold}"
            )

            channel.on(
                "postgres_changes",
                {
                    "event": "*",  # INSERT and UPDATE
                    "schema": "public",
                    "table": self.config.TABLES["emails"],
                    "filter": table_filter,
                },
                self._wrap_callback(callback, "urgent_email"),
            )

            channel.subscribe()
            self.channels[channel_name] = channel

            logger.info(
                "Subscribed to urgent emails "
                f"(threshold: {urgency_threshold}) "
                f"for user {self.current_user_id}"
            )
            return channel_name

        except Exception as e:
            logger.error(f"Failed to subscribe to urgent emails: {str(e)}")
            raise

    def subscribe_to_task_updates(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Subscribe to task status updates.

        Args:
            callback: Function to call when tasks are updated

        Returns:
            Subscription ID
        """
        if not self._is_connected:
            raise RuntimeError("Real-time interface not connected")

        channel_name = f"task_updates_{self.current_user_id}"

        try:
            channel = self.client.channel(channel_name)

            # Filter for user's tasks
            table_filter = f"user_id=eq.{self.current_user_id}"

            channel.on(
                "postgres_changes",
                {
                    "event": "*",  # All events
                    "schema": "public",
                    "table": self.config.TABLES["email_tasks"],
                    "filter": table_filter,
                },
                self._wrap_callback(callback, "task_update"),
            )

            channel.subscribe()
            self.channels[channel_name] = channel

            logger.info(f"Subscribed to task updates for user {self.current_user_id}")
            return channel_name

        except Exception as e:
            logger.error(f"Failed to subscribe to task updates: {str(e)}")
            raise

    def subscribe_to_ai_processing(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Subscribe to AI processing completion notifications.

        Args:
            callback: Function to call when AI processing completes

        Returns:
            Subscription ID
        """
        if not self._is_connected:
            raise RuntimeError("Real-time interface not connected")

        channel_name = f"ai_processing_{self.current_user_id}"

        try:
            channel = self.client.channel(channel_name)

            # Filter for AI processing updates
            table_filter = (
                f"user_id=eq.{self.current_user_id},ai_processing_enabled=eq.true"
            )

            channel.on(
                "postgres_changes",
                {
                    "event": "UPDATE",
                    "schema": "public",
                    "table": self.config.TABLES["emails"],
                    "filter": table_filter,
                },
                self._wrap_callback(callback, "ai_processing_complete"),
            )

            channel.subscribe()
            self.channels[channel_name] = channel

            logger.info(
                f"Subscribed to AI processing updates for user {self.current_user_id}"
            )
            return channel_name

        except Exception as e:
            logger.error(f"Failed to subscribe to AI processing: {str(e)}")
            raise

    def subscribe_to_analytics_updates(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Subscribe to analytics and stats updates.

        Args:
            callback: Function to call when analytics update

        Returns:
            Subscription ID
        """
        if not self._is_connected:
            raise RuntimeError("Real-time interface not connected")

        channel_name = f"analytics_{self.current_user_id}"

        try:
            channel = self.client.channel(channel_name)

            # Filter for user's analytics
            table_filter = f"user_id=eq.{self.current_user_id}"

            channel.on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": self.config.TABLES["email_analytics"],
                    "filter": table_filter,
                },
                self._wrap_callback(callback, "analytics_update"),
            )

            channel.subscribe()
            self.channels[channel_name] = channel

            logger.info(
                f"Subscribed to analytics updates for user {self.current_user_id}"
            )
            return channel_name

        except Exception as e:
            logger.error(f"Failed to subscribe to analytics: {str(e)}")
            raise

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a specific channel.

        Args:
            subscription_id: Channel/subscription ID to unsubscribe from

        Returns:
            bool: Success status
        """
        try:
            if subscription_id in self.channels:
                self.channels[subscription_id].unsubscribe()
                del self.channels[subscription_id]
                logger.info(f"Unsubscribed from channel: {subscription_id}")
                return True
            else:
                logger.warning(f"Subscription not found: {subscription_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {subscription_id}: {str(e)}")
            return False

    def _wrap_callback(
        self, user_callback: Callable[[Dict[str, Any]], None], event_type: str
    ) -> Callable[[Dict[str, Any]], None]:
        """
        Wrap user callback with error handling and event enrichment.

        Args:
            user_callback: User's callback function
            event_type: Type of event for logging

        Returns:
            Wrapped callback function
        """

        def wrapper(payload: Dict[str, Any]) -> None:
            try:
                # Enrich payload with metadata
                enriched_payload = {
                    "event_type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": self.current_user_id,
                    "data": payload,
                }

                # Call user callback
                user_callback(enriched_payload)

            except Exception as e:
                logger.error(f"Error in real-time callback for {event_type}: {str(e)}")

        return wrapper

    def get_active_subscriptions(self) -> List[str]:
        """
        Get list of active subscription IDs.

        Returns:
            List of active subscription/channel IDs
        """
        return list(self.channels.keys())

    def get_subscription_count(self) -> int:
        """
        Get number of active subscriptions.

        Returns:
            Number of active subscriptions
        """
        return len(self.channels)

    async def send_test_notification(
        self, event_type: str = "test", data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a test notification (for development/debugging).

        Args:
            event_type: Type of test event
            data: Optional test data

        Returns:
            bool: Success status
        """
        try:
            test_payload = {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": self.current_user_id,
                "data": data or {"message": "Test notification"},
                "is_test": True,
            }

            # For now, just log the test notification
            # In a real implementation, you might insert into a test table
            # that triggers real-time notifications
            logger.info(f"Test notification sent: {test_payload}")
            return True

        except Exception as e:
            logger.error(f"Failed to send test notification: {str(e)}")
            return False

    def is_connected(self) -> bool:
        """
        Check if real-time interface is connected.

        Returns:
            bool: Connection status
        """
        return self._is_connected

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information and status.

        Returns:
            Dictionary with connection details
        """
        return {
            "connected": self._is_connected,
            "user_id": self.current_user_id,
            "active_subscriptions": len(self.channels),
            "channels": list(self.channels.keys()),
            "realtime_enabled": self.config.realtime_enabled,
        }
