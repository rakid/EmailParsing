"""
Supabase Plugin Implementation

This module implements the PluginInterface for Supabase integration, providing
a complete plugin that integrates multi-user database capabilities, real-time
features, and authentication into the existing email processing system.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.integrations import PluginInterface
from src.models import ProcessedEmail

from .auth_interface import SupabaseAuthInterface
from .config import SupabaseConfig
from .database_interface import SupabaseDatabaseInterface
from .realtime import SupabaseRealtimeInterface
from .user_management import UserManagementInterface

logger = logging.getLogger(__name__)


class SupabasePlugin(PluginInterface):
    """
    Supabase integration plugin for the Email Parsing MCP Server.

    This plugin provides:
    - Multi-user database storage with RLS
    - Real-time email processing notifications
    - User authentication and authorization
    - Analytics and dashboard data
    - Seamless integration with existing workflow
    """

    def __init__(self, config: Optional[SupabaseConfig] = None):
        """
        Initialize Supabase plugin.

        Args:
            config: Optional SupabaseConfig instance
        """
        self.config = config or SupabaseConfig()
        self.database = SupabaseDatabaseInterface(self.config)
        self.auth: Optional[SupabaseAuthInterface] = (
            None  # Will be initialized when database connects
        )
        self.realtime: Optional[SupabaseRealtimeInterface] = (
            None  # Will be initialized when database connects
        )
        self.user_management: Optional[UserManagementInterface] = (
            None  # Will be initialized when database connects
        )
        self.name = "supabase"
        self.version = "1.0.0"
        self.description = "Supabase multi-user database and real-time integration"
        self.enabled = True
        self._initialized = False
        self._real_time_subscriptions: Dict[str, Any] = {}

    def get_name(self) -> str:
        """Get plugin name"""
        return self.name

    def get_version(self) -> str:
        """Get plugin version"""
        return self.version

    def get_dependencies(self) -> List[str]:
        """Get required dependencies"""
        return ["supabase>=2.0.0", "aiohttp", "asyncio"]

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata for testing and information purposes"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "initialized": self._initialized,
            "capabilities": [
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
            ],
        }

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Supabase plugin.

        Args:
            config: Optional configuration dictionary
                (for PluginInterface compatibility)
        """
        try:
            logger.info("Initializing Supabase plugin...")

            # Override config if provided
            if config:
                # Update config with provided values
                for key, value in config.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

            # Connect to Supabase
            await self.database.connect()

            # Initialize auth and realtime interfaces with the database client
            if self.database.client:
                self.auth = SupabaseAuthInterface(self.database.client, self.config)
                self.realtime = SupabaseRealtimeInterface(
                    self.database.client, self.config
                )
                self.user_management = UserManagementInterface(
                    self.database.client, self.config
                )

                logger.info(
                    "Supabase auth, realtime, and user management "
                    "interfaces initialized"
                )

            self._initialized = True
            logger.info("Supabase plugin initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase plugin: {str(e)}")
            raise

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """
        Process email through Supabase plugin.

        This method:
        1. Takes a ProcessedEmail instance
        2. Stores it in Supabase with RLS
        3. Triggers real-time notifications
        4. Returns the enhanced processed email

        Args:
            email: ProcessedEmail instance to process

        Returns:
            Enhanced ProcessedEmail instance
        """
        if not self._initialized or not self.enabled:
            logger.warning("Supabase plugin not initialized or disabled")
            return email

        try:
            logger.info(
                f"Processing email through Supabase: {email.email_data.subject}"
            )

            # Store email in Supabase
            email_id = await self.database.store_email(email)

            # Add Supabase-specific metadata
            if not email.analysis:
                from src.models import EmailAnalysis

                email.analysis = EmailAnalysis(
                    urgency_score=self._calculate_urgency_score(email.email_data),
                    urgency_level=self._determine_urgency_level(email.email_data),
                    sentiment="neutral",
                    confidence=0.8,
                    keywords=["supabase_processed"],
                    action_items=[],
                    temporal_references=[],
                    tags=["supabase"],
                    category="supabase_analyzed",
                )

            # Add Supabase-specific tags if not already present
            if email.analysis and email.analysis.tags:
                if "supabase" not in email.analysis.tags:
                    email.analysis.tags.append("supabase")

            # Store in Supabase database
            logger.info(f"Email stored in Supabase with ID: {email_id}")

            # Trigger real-time notification
            await self._trigger_real_time_notification(
                "email_processed",
                {
                    "email_id": email_id,
                    "subject": email.email_data.subject,
                    "sender": email.email_data.from_email,
                    "priority": (
                        email.priority if hasattr(email, "priority") else "medium"
                    ),
                    "processed_at": datetime.now().isoformat(),
                },
            )

            return email

        except Exception as e:
            logger.error(f"Failed to process email through Supabase: {str(e)}")
            return email

    def _calculate_urgency_score(self, email_data) -> int:
        """Calculate urgency score for email."""
        # Simple urgency calculation based on keywords and sender
        score = 50  # Base score

        if email_data.subject:
            urgent_keywords = ["urgent", "emergency", "asap", "immediate", "critical"]
            for keyword in urgent_keywords:
                if keyword.lower() in email_data.subject.lower():
                    score += 20

        return min(score, 100)

    def _determine_urgency_level(self, email_data):
        """Determine urgency level from email data."""
        from src.models import UrgencyLevel

        score = self._calculate_urgency_score(email_data)
        if score >= 80:
            return UrgencyLevel.CRITICAL
        elif score >= 60:
            return UrgencyLevel.HIGH
        elif score >= 40:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW

    async def _trigger_real_time_notification(
        self, event_type: str, data: Dict[str, Any]
    ) -> None:
        """Trigger real-time notification."""
        if self.realtime:
            try:
                await self.realtime.send_test_notification(event_type, data)
            except Exception as e:
                logger.error(f"Failed to trigger real-time notification: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        try:
            logger.info("Cleaning up Supabase plugin...")

            # Close real-time subscriptions
            for subscription_id, channel in self._real_time_subscriptions.items():
                try:
                    channel.unsubscribe()
                    logger.info(f"Unsubscribed from channel: {subscription_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to unsubscribe from {subscription_id}: {str(e)}"
                    )

            self._real_time_subscriptions.clear()

            # Disconnect from database
            await self.database.disconnect()

            self._initialized = False
            logger.info("Supabase plugin cleanup completed")

        except Exception as e:
            logger.error(f"Error during Supabase plugin cleanup: {str(e)}")

    # User Management Methods

    async def authenticate_user(self, email: str, password: str) -> bool:
        """
        Authenticate user through Supabase Auth.

        Args:
            email: User email
            password: User password

        Returns:
            bool: True if authentication successful
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        return await self.database.authenticate_user(email, password)

    async def register_user(
        self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register new user through Supabase Auth.

        Args:
            email: User email
            password: User password
            metadata: Additional user metadata

        Returns:
            str: User ID
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        return await self.database.register_user(email, password, metadata)

    def get_current_user_id(self) -> Optional[str]:
        """Get current authenticated user ID."""
        return self.database.get_current_user_id()

    # Email Management Methods

    async def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        """
        Retrieve email by ID.

        Args:
            email_id: Email ID to retrieve

        Returns:
            ProcessedEmail instance or None if not found
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        return await self.database.get_email(email_id)

    async def search_emails(self, query: Dict[str, Any]) -> List[ProcessedEmail]:
        """
        Search emails with filters.

        Args:
            query: Search parameters

        Returns:
            List of ProcessedEmail instances
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        return await self.database.search_emails(query)

    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get current user's email processing statistics.

        Returns:
            Dictionary with user statistics
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        stats = await self.database.get_stats()
        return {
            "total_processed": stats.total_processed,
            "total_errors": stats.total_errors,
            "avg_urgency_score": stats.avg_urgency_score,
            "urgency_distribution": stats.urgency_distribution,
            "last_processed": (
                stats.last_processed.isoformat() if stats.last_processed else None
            ),
            "processing_times": stats.processing_times,
        }

    # Real-time Methods

    async def subscribe_to_email_changes(
        self, callback, filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Subscribe to real-time email changes.

        Args:
            callback: Function to call on changes
            filters: Optional filters for subscription

        Returns:
            str: Subscription ID
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        try:
            # Create unique subscription ID
            subscription_id = f"email_changes_{len(self._real_time_subscriptions)}"

            # Set up real-time subscription
            channel = self.database.subscribe_to_email_changes(callback, filters)

            # Store subscription for cleanup
            self._real_time_subscriptions[subscription_id] = channel

            logger.info(f"Created real-time subscription: {subscription_id}")
            return subscription_id

        except Exception as e:
            logger.error(f"Failed to create real-time subscription: {str(e)}")
            raise

    async def unsubscribe_from_email_changes(self, subscription_id: str) -> bool:
        """
        Unsubscribe from real-time email changes.

        Args:
            subscription_id: Subscription ID to remove

        Returns:
            bool: True if unsubscribed successfully
        """
        if subscription_id in self._real_time_subscriptions:
            try:
                channel = self._real_time_subscriptions.pop(subscription_id)
                channel.unsubscribe()
                logger.info(f"Unsubscribed from: {subscription_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {subscription_id}: {str(e)}")
                return False

        return False

    # Supabase-specific MCP tools for enhanced functionality

    async def get_realtime_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get real-time statistics for the user.

        Args:
            user_id: User ID for filtering

        Returns:
            Dictionary with real-time stats
        """
        if not self._initialized or not self.database:
            raise RuntimeError("Plugin not initialized")

        try:
            await self.database.set_user_context(user_id)

            # Get AI-enhanced emails
            ai_emails = await self.database.get_ai_enhanced_emails(limit=10)

            # Get urgent emails
            urgent_emails = await self.database.get_urgent_emails_realtime()

            # Get user quota status
            quota_status: Dict[str, Any] = (
                await self.auth.get_user_quota_status(user_id) if self.auth else {}
            )

            # Get basic stats
            stats = await self.database.get_stats()

            return {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "ai_enhanced_emails": len(ai_emails),
                "urgent_emails": len(urgent_emails),
                "quota_status": quota_status,
                "total_processed": stats.total_processed,
                "total_errors": stats.total_errors,
                "avg_urgency_score": stats.avg_urgency_score,
            }

        except Exception as e:
            logger.error(f"Failed to get realtime stats: {str(e)}")
            return {
                "error": str(e),
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }

    async def subscribe_to_email_updates(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Subscribe to real-time email updates.

        Args:
            user_id: User ID
            callback: Callback function for updates
            filters: Optional filters

        Returns:
            Subscription ID
        """
        if not self._initialized or not self.realtime:
            raise RuntimeError("Plugin not initialized or realtime not available")

        try:
            await self.realtime.connect(user_id)
            subscription_id = self.realtime.subscribe_to_new_emails(callback, filters)

            # Store subscription for cleanup
            self._real_time_subscriptions[subscription_id] = {
                "user_id": user_id,
                "type": "email_updates",
                "created_at": datetime.now().isoformat(),
            }

            return subscription_id

        except Exception as e:
            logger.error(f"Failed to subscribe to email updates: {str(e)}")
            raise

    async def get_ai_enhanced_emails_by_user(
        self, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get AI-enhanced emails for specific user.

        Args:
            user_id: User ID
            limit: Maximum number of emails to return

        Returns:
            List of AI-enhanced email data
        """
        if not self._initialized or not self.database:
            raise RuntimeError("Plugin not initialized")

        try:
            await self.database.set_user_context(user_id)
            return await self.database.get_ai_enhanced_emails(limit)
        except Exception as e:
            logger.error(f"Failed to get AI enhanced emails: {str(e)}")
            return []

    async def authenticate_user_session(
        self, email: str, password: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Authenticate user and return session info.

        Args:
            email: User email
            password: User password

        Returns:
            Tuple of (success, user_id, session_info)
        """
        if not self._initialized or not self.auth:
            raise RuntimeError("Plugin not initialized or auth not available")

        try:
            success, user_id, error = await self.auth.authenticate_user(email, password)

            if success and user_id:
                # Get session info
                session_info = self.auth.get_current_session()
                return True, user_id, session_info
            else:
                return False, None, {"error": error}

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False, None, {"error": str(e)}
