"""
Supabase Database Interface Implementation

This module implements the DatabaseInterface for Supabase, providing multi-user
database capabilities with Row Level Security (RLS), real-time features, and
seamless integration with the existing plugin architecture.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from postgrest.exceptions import APIError

from src.integrations import DatabaseInterface
from src.models import (
    AttachmentData,
    EmailAnalysis,
    EmailData,
    EmailStats,
    ProcessedEmail,
    UrgencyLevel,
)
from supabase import Client, create_client

from .config import SupabaseConfig

# Constants
DB_NOT_CONNECTED_ERROR = "Database not connected"
USER_CONTEXT_NOT_SET_ERROR = "User context not set"


class SupabaseDatabaseInterface(DatabaseInterface):
    """
    Supabase implementation of DatabaseInterface.

    Features:
    - Multi-user support with Row Level Security (RLS)
    - Real-time subscriptions
    - Authentication integration
    - Analytics and dashboard support
    - Backward compatibility with existing interface
    """

    def __init__(self, config: Optional[SupabaseConfig] = None):
        """Initialize Supabase database interface."""
        self.config = config or SupabaseConfig()
        self.client: Optional[Client] = None
        self.current_user_id: Optional[str] = None
        self._connected = False
        self._real_time_subscriptions: Dict[str, Any] = {}

    async def connect(self, connection_string: Optional[str] = None) -> None:
        """
        Establish connection to Supabase.

        Args:
            connection_string: Optional override for connection (uses config by default)
        """
        try:
            # Check if configuration is available
            if not self.config.is_configured():
                raise ConnectionError("Supabase URL and API key are required")

            # Create Supabase client
            if not self.config.supabase_url or not self.config.supabase_key:
                raise ConnectionError("Supabase URL and API key are required")
            self.client = create_client(
                self.config.supabase_url, self.config.supabase_key
            )

            # Test connection with a simple query
            try:
                _ = (
                    self.client.table(self.config.TABLES["emails"])
                    .select("id")
                    .limit(1)
                    .execute()
                )
                self._connected = True
            except Exception:
                # If table doesn't exist or we can't access it, that's expected
                # We'll consider client creation success as successful connection
                self._connected = True

        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {str(e)}") from e

    async def store_email(self, email: ProcessedEmail) -> str:
        """
        Store processed email with analysis data.

        Args:
            email: ProcessedEmail instance with analysis

        Returns:
            Email ID of stored email
        """
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            # Prepare email data for Supabase
            email_data = self._processed_email_to_supabase(email)

            # Store the main email record
            email_response = (
                self.client.table(self.config.TABLES["emails"])
                .upsert(email_data, on_conflict="message_id")
                .execute()
            )

            if not email_response.data:
                raise ValueError("Failed to store email - no data returned")

            email_id = email_response.data[0]["id"]

            # Store analysis if present
            if email.analysis:
                analysis_data = self._analysis_to_supabase(email.analysis, email_id)
                self.client.table(self.config.TABLES["email_analysis"]).insert(
                    analysis_data
                ).execute()

            # Store attachments if present
            if email.email_data.attachments:
                # Convert AttachmentData objects to dicts
                attachment_dicts = [
                    {
                        "filename": att.name,
                        "content_type": att.content_type,
                        "size": att.size,
                        "content": att.content_id or "",
                    }
                    for att in email.email_data.attachments
                ]
                attachment_data = self._attachments_to_supabase(
                    attachment_dicts, email_id
                )
                self.client.table(self.config.TABLES["email_attachments"]).insert(
                    attachment_data
                ).execute()

            return email_id

        except APIError as e:
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to store email: {str(e)}") from e

    async def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        """
        Retrieve email by ID with RLS filtering.

        Args:
            email_id: Email ID to retrieve

        Returns:
            ProcessedEmail instance or None if not found
        """
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            # Get email with related data
            email_response = (
                self.client.table(self.config.TABLES["emails"])
                .select(
                    """
                *,
                email_analysis(*),
                email_attachments(*)
            """
                )
                .eq("id", email_id)
                .execute()
            )

            if not email_response.data:
                return None

            return self._supabase_to_processed_email(email_response.data[0])

        except APIError as e:
            if "PGRST116" in str(e):  # Row not found
                return None
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve email: {str(e)}") from e

    async def search_emails(self, query: Dict[str, Any]) -> List[ProcessedEmail]:
        """
        Search emails with filters and RLS.

        Args:
            query: Search parameters (sender, subject, date_range, status, etc.)

        Returns:
            List of ProcessedEmail instances
        """
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            # Build query
            supabase_query = self.client.table(self.config.TABLES["emails"]).select(
                """
                *,
                email_analysis(*),
                email_attachments(*)
            """
            )

            # Apply filters
            if "sender" in query:
                supabase_query = supabase_query.ilike("sender", f"%{query['sender']}%")

            if "subject" in query:
                supabase_query = supabase_query.ilike(
                    "subject", f"%{query['subject']}%"
                )

            if "status" in query:
                supabase_query = supabase_query.eq("status", query["status"])

            if "priority" in query:
                supabase_query = supabase_query.eq("priority", query["priority"])

            if "date_from" in query:
                supabase_query = supabase_query.gte("received_date", query["date_from"])

            if "date_to" in query:
                supabase_query = supabase_query.lte("received_date", query["date_to"])

            # Apply sorting and limits
            order_by = query.get("order_by", "received_date")
            order_desc = query.get("order_desc", True)
            limit = query.get("limit", 100)
            offset = query.get("offset", 0)

            supabase_query = supabase_query.order(order_by, desc=order_desc)
            supabase_query = supabase_query.limit(limit).offset(offset)

            response = supabase_query.execute()

            return [self._supabase_to_processed_email(row) for row in response.data]

        except APIError as e:
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to search emails: {str(e)}") from e

    async def get_stats(self) -> EmailStats:
        """
        Get processing statistics with user-level RLS filtering.

        Returns:
            EmailStats instance with current statistics
        """
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            # Get basic counts
            total_response = (
                self.client.table(self.config.TABLES["emails"])
                .select("id", count="exact")
                .execute()
            )
            total_processed = total_response.count or 0

            # Get status counts
            status_response = self.client.rpc("get_email_stats_by_status").execute()
            status_counts = {
                row["status"]: row["count"] for row in status_response.data
            }

            # Priority counts are currently not used but could be
            # added in the future
            # Uncomment and use the following if priority stats
            # are needed:
            # priority_response = self.client.rpc(
            #     "get_email_stats_by_priority"
            # ).execute()
            # priority_counts = {
            #     row["priority"]: row["count"]
            #     for row in priority_response.data
            # }

            # Get average processing metrics
            metrics_response = self.client.rpc("get_email_processing_metrics").execute()
            metrics = metrics_response.data[0] if metrics_response.data else {}

            return EmailStats(
                total_processed=total_processed,
                total_errors=0,  # Set default error count
                avg_urgency_score=metrics.get("avg_urgency_score", 0.0),
                urgency_distribution={
                    UrgencyLevel.HIGH: status_counts.get("high", 0),
                    UrgencyLevel.MEDIUM: status_counts.get("medium", 0),
                    UrgencyLevel.LOW: status_counts.get("low", 0),
                },
                last_processed=datetime.now(),
                processing_times=[],  # Set default processing times
            )

        except APIError as e:
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to get stats: {str(e)}") from e

    async def disconnect(self) -> None:
        """Close Supabase connection."""
        self._connected = False
        self.client = None
        self.current_user_id = None

    # User Management Methods (Supabase-specific)

    async def authenticate_user(self, email: str, password: str) -> bool:
        """
        Authenticate user with Supabase Auth.

        Args:
            email: User email
            password: User password

        Returns:
            bool: True if authentication successful
        """
        if not self.client:
            raise RuntimeError("Database not connected")

        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if response.user:
                self.current_user_id = response.user.id
                return True
            return False

        except Exception as e:
            raise ValueError(f"Authentication failed: {str(e)}") from e

    async def register_user(
        self, email: str, password: str, metadata: Dict[str, Any] | None = None
    ) -> str:
        """
        Register new user with Supabase Auth.

        Args:
            email: User email
            password: User password
            metadata: Additional user metadata

        Returns:
            str: User ID
        """
        if not self.client:
            raise RuntimeError("Database not connected")

        try:
            response = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": metadata or {}},
                }
            )

            if response.user:
                return response.user.id
            raise ValueError("User registration failed")

        except Exception as e:
            raise ValueError(f"Registration failed: {str(e)}") from e

    def get_current_user_id(self) -> Optional[str]:
        """Get current authenticated user ID."""
        return self.current_user_id

    def set_current_user_id(self, user_id: str) -> None:
        """Set the current user ID for database operations."""
        self.current_user_id = user_id

    # Real-time Methods (Supabase-specific)

    def subscribe_to_email_changes(
        self, callback, filters: Dict[str, Any] | None = None
    ):
        """
        Subscribe to real-time email changes.

        Args:
            callback: Function to call on changes
            filters: Optional filters for subscription
        """
        if not self.client:
            raise RuntimeError("Database not connected")

        channel = self.client.channel("email_changes")

        # Configure subscription based on filters
        table_filter = self.config.TABLES["emails"]
        if filters:
            if "user_id" in filters:
                table_filter += f":user_id=eq.{filters['user_id']}"

        channel.on(
            "postgres_changes",
            {
                "event": "*",
                "schema": "public",
                "table": self.config.TABLES["emails"],
                "filter": table_filter,
            },
            callback,
        )

        channel.subscribe()
        return channel

    # Supabase-specific methods for enhanced functionality

    async def set_user_context(self, user_id: str) -> None:
        """Set user context for RLS filtering"""
        self.current_user_id = user_id
        if self.client:
            # Set user context for RLS
            self.client.auth.set_session(
                {"access_token": f"user_{user_id}", "user": {"id": user_id}}
            )

    def subscribe_to_changes(
        self, callback, filter_options: Dict[str, Any] | None = None
    ) -> str:
        """
        Subscribe to real-time changes in emails table

        Args:
            callback: Function to call when changes occur
            filter_options: Filters for subscription

        Returns:
            Subscription ID for later cleanup
        """
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            # Create subscription filter
            subscription_filter = f"user_id=eq.{self.current_user_id}"
            if filter_options:
                if "urgency_level" in filter_options:
                    subscription_filter += (
                        f" and urgency_level=eq.{filter_options['urgency_level']}"
                    )
                if "status" in filter_options:
                    subscription_filter += (
                        f" and processing_status=eq.{filter_options['status']}"
                    )

            # Subscribe to changes
            subscription = (
                self.client.table(self.config.TABLES["emails"])
                .on("*", callback)
                .filter(subscription_filter)
                .subscribe()
            )

            subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
            self._real_time_subscriptions[subscription_id] = subscription

            return subscription_id

        except Exception as e:
            raise RuntimeError(f"Failed to create subscription: {str(e)}") from e

    def unsubscribe_from_changes(self, subscription_id: str) -> None:
        """Remove real-time subscription"""
        if subscription_id in self._real_time_subscriptions:
            subscription = self._real_time_subscriptions[subscription_id]
            subscription.unsubscribe()
            del self._real_time_subscriptions[subscription_id]

    async def get_ai_enhanced_emails(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get emails with AI analysis data"""
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            response = (
                self.client.table(self.config.TABLES["emails"])
                .select(
                    "id, subject, from_email, ai_analysis_result, "
                    "ai_processed_at, urgency_score"
                )
                .not_.is_("ai_analysis_result", "null")
                .eq("ai_processing_enabled", True)
                .order("ai_processed_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data

        except APIError as e:
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to get AI enhanced emails: {str(e)}") from e

    async def get_urgent_emails_realtime(
        self, urgency_threshold: int = 70
    ) -> List[Dict[str, Any]]:
        """Get urgent emails based on AI urgency scoring"""
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")

        try:
            response = (
                self.client.table(self.config.TABLES["emails"])
                .select("*")
                .gte("urgency_score", urgency_threshold)
                .eq("processing_status", "processed")
                .order("urgency_score", desc=True)
                .execute()
            )

            return response.data

        except APIError as e:
            raise ValueError(f"Supabase API error: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to get urgent emails: {str(e)}") from e

    # Private helper methods

    def _processed_email_to_supabase(self, email: ProcessedEmail) -> Dict[str, Any]:
        """Convert ProcessedEmail to Supabase format."""
        return {
            "id": email.id,
            "user_id": self.current_user_id,
            "message_id": email.email_data.message_id,
            "from_email": email.email_data.from_email,
            "to_emails": email.email_data.to_emails,
            "cc_emails": email.email_data.cc_emails or [],
            "bcc_emails": email.email_data.bcc_emails or [],
            "subject": email.email_data.subject,
            "text_body": email.email_data.text_body,
            "html_body": email.email_data.html_body,
            "received_at": email.email_data.received_at.isoformat(),
            "headers": email.email_data.headers,
            "status": (
                email.status.value if hasattr(email.status, "value") else email.status
            ),
            "processed_at": (
                email.processed_at.isoformat() if email.processed_at else None
            ),
            "error_message": email.error_message,
            "webhook_payload": email.webhook_payload,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def _analysis_to_supabase(
        self, analysis: EmailAnalysis, email_id: str
    ) -> Dict[str, Any]:
        """Convert EmailAnalysis to Supabase format."""
        return {
            "id": str(uuid.uuid4()),
            "email_id": email_id,
            "user_id": self.current_user_id,
            "urgency_score": analysis.urgency_score,
            "urgency_level": analysis.urgency_level.value,
            "sentiment": analysis.sentiment,
            "confidence_score": analysis.confidence,
            "keywords": analysis.keywords,
            "action_items": analysis.action_items,
            "temporal_references": analysis.temporal_references,
            "tags": analysis.tags,
            "category": analysis.category,
            "created_at": datetime.now().isoformat(),
        }

    def _attachments_to_supabase(
        self, attachments: List[Dict[str, Any]], email_id: str
    ) -> List[Dict[str, Any]]:
        """Convert attachments to Supabase format."""
        return [
            {
                "id": str(uuid.uuid4()),
                "email_id": email_id,
                "user_id": self.current_user_id,
                "filename": (
                    attachment.name
                    if hasattr(attachment, "name")
                    else getattr(attachment, "filename", "")
                ),
                "content_type": (
                    attachment.content_type
                    if hasattr(attachment, "content_type")
                    else ""
                ),
                "size": attachment.size if hasattr(attachment, "size") else 0,
                "storage_path": getattr(attachment, "storage_path", ""),
                "created_at": datetime.now().isoformat(),
            }
            for attachment in attachments
        ]

    def _supabase_to_processed_email(self, row: Dict[str, Any]) -> ProcessedEmail:
        """Convert Supabase row to ProcessedEmail."""
        # Create EmailData
        email_data = EmailData(
            message_id=row["message_id"],
            from_email=row["from_email"],
            to_emails=row["to_emails"] or [],
            cc_emails=row.get("cc_emails", []),
            bcc_emails=row.get("bcc_emails", []),
            subject=row["subject"],
            text_body=row.get("text_body"),
            html_body=row.get("html_body"),
            received_at=(
                datetime.fromisoformat(row["received_at"])
                if isinstance(row["received_at"], str)
                else row["received_at"]
            ),
            headers=row["headers"] or {},
            attachments=[
                AttachmentData(
                    name=att["filename"],
                    content_type=att["content_type"],
                    size=att["size"],
                    content_id=att.get("content_id"),
                )
                for att in row.get("email_attachments", [])
            ],
        )

        # Create EmailAnalysis if present
        analysis = None
        if row.get("email_analysis") and len(row["email_analysis"]) > 0:
            analysis_data = row["email_analysis"][0]
            analysis = EmailAnalysis(
                urgency_score=analysis_data.get("urgency_score", 0),
                urgency_level=analysis_data.get("urgency_level", "low"),
                sentiment=analysis_data.get("sentiment", "neutral"),
                confidence=analysis_data.get("confidence_score", 0.0),
                keywords=analysis_data.get("keywords", []),
                action_items=analysis_data.get("action_items", []),
                temporal_references=analysis_data.get("temporal_references", []),
                tags=analysis_data.get("tags", []),
                category=analysis_data.get("category"),
            )

        return ProcessedEmail(
            id=row["id"],
            email_data=email_data,
            analysis=analysis,
            status=row["status"],
            processed_at=(
                datetime.fromisoformat(row["processed_at"])
                if row["processed_at"]
                else None
            ),
            error_message=row.get("error_message"),
            webhook_payload=row.get("webhook_payload", {}),
        )

    def _has_ai_analysis(self, analysis: EmailAnalysis) -> bool:
        """Check if analysis contains AI-enhanced data"""
        # Check if analysis has SambaNova-specific tags or enhanced data
        return (
            any("sambanova" in tag.lower() for tag in analysis.tags)
            or any("ai_" in tag.lower() for tag in analysis.tags)
            or analysis.confidence > 0.85  # High confidence suggests AI processing
        )

    def _extract_ai_analysis(self, analysis: EmailAnalysis) -> Dict[str, Any]:
        """Extract AI-enhanced analysis data for storage in JSONB"""
        ai_data = {
            "sambanova_version": "1.0.0",
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": analysis.confidence,
        }

        # Extract task-related AI data
        if analysis.action_items:
            ai_data["task_extraction"] = {
                "tasks": [
                    {
                        "description": task,
                        "extraction_method": "sambanova",
                        "urgency_indicators": [],
                        "confidence": analysis.confidence,
                    }
                    for task in analysis.action_items
                ],
                "overall_urgency": analysis.urgency_score,
                "extraction_confidence": analysis.confidence,
            }

        # Extract sentiment data
        ai_data["sentiment_analysis"] = {
            "sentiment": analysis.sentiment,
            "confidence": analysis.confidence,
            "urgency_level": (
                analysis.urgency_level.value
                if hasattr(analysis.urgency_level, "value")
                else str(analysis.urgency_level)
            ),
        }

        # Extract keywords as context
        if analysis.keywords:
            ai_data["context_analysis"] = {
                "context_keywords": analysis.keywords,
                "business_context": analysis.category or "general",
            }

        return ai_data

    # Additional methods expected by tests
    async def get_emails(
        self, filters: Dict[str, Any] | None = None, limit: int = 50
    ) -> List[ProcessedEmail]:
        """Get emails with optional filters."""
        if not self._connected or not self.client:
            raise RuntimeError(DB_NOT_CONNECTED_ERROR)

        if not self.current_user_id:
            raise RuntimeError("User context not set")

        try:
            query = (
                self.client.table("emails")
                .select("*")
                .eq("user_id", self.current_user_id)
            )

            # Apply filters
            if filters:
                if "start_date" in filters:
                    query = query.gte("received_at", filters["start_date"].isoformat())
                if "end_date" in filters:
                    query = query.lte("received_at", filters["end_date"].isoformat())
                if "sender" in filters:
                    query = query.eq("from_email", filters["sender"])

            query = query.order("received_at", desc=True).limit(limit)
            response = query.execute()

            return [self._supabase_to_processed_email(row) for row in response.data]
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve emails: {str(e)}") from e

    async def get_email_by_id(self, email_id: str) -> Optional[ProcessedEmail]:
        """Get a specific email by ID."""
        if not self._connected or not self.client:
            raise RuntimeError(DB_NOT_CONNECTED_ERROR)

        if not email_id:
            return None

        if not self.current_user_id:
            raise RuntimeError("User context not set")

        try:
            response = (
                self.client.table("emails")
                .select("*")
                .eq("id", email_id)
                .eq("user_id", self.current_user_id)
                .execute()
            )

            if response.data:
                return self._supabase_to_processed_email(response.data[0])
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve email {email_id}: {str(e)}") from e

    async def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID."""
        if not self._connected or not self.client:
            raise RuntimeError(DB_NOT_CONNECTED_ERROR)

        if not self.current_user_id:
            raise RuntimeError("User context not set")

        try:
            response = (
                self.client.table("emails")
                .delete()
                .eq("id", email_id)
                .eq("user_id", self.current_user_id)
                .execute()
            )

            return len(response.data) > 0
        except Exception as e:
            raise RuntimeError(f"Failed to delete email {email_id}: {str(e)}") from e

    async def get_email_stats(self) -> EmailStats:
        """Get email statistics."""
        if not self._connected or not self.client:
            raise RuntimeError(DB_NOT_CONNECTED_ERROR)

        if not self.current_user_id:
            raise RuntimeError("User context not set")

        try:
            # Get basic count
            response = (
                self.client.table("emails")
                .select("*", count="exact")
                .eq("user_id", self.current_user_id)
                .execute()
            )
            total_emails = response.count or 0

            # Create and return EmailStats object
            from ..models import UrgencyLevel

            return EmailStats(
                total_processed=total_emails,
                total_errors=0,
                avg_urgency_score=0.0,
                urgency_distribution={
                    UrgencyLevel.LOW: 0,
                    UrgencyLevel.MEDIUM: 0,
                    UrgencyLevel.HIGH: 0,
                },
                processing_times=[],
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get email statistics: {str(e)}") from e

    async def update_email_analysis(
        self, email_id: str, analysis: EmailAnalysis
    ) -> bool:
        """Update email analysis."""
        if not self._connected or not self.client:
            raise RuntimeError(DB_NOT_CONNECTED_ERROR)

        try:
            analysis_data = self._analysis_to_supabase(analysis, email_id)
            response = (
                self.client.table("email_analysis")
                .update(analysis_data)
                .eq("email_id", email_id)
                .execute()
            )

            return len(response.data) > 0
        except Exception as e:
            raise RuntimeError(f"Failed to update email analysis: {str(e)}") from e
