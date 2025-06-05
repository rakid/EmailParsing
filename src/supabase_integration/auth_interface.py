"""
Supabase Authentication Interface

This module provides authentication and user management capabilities
for the Supabase integration, including user registration, login,
session management, and profile management.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from supabase import Client

from .config import SupabaseConfig

logger = logging.getLogger(__name__)


class SupabaseAuthInterface:
    """
    Supabase authentication interface for user management.

    Features:
    - User registration and authentication
    - Session management
    - Profile management
    - Password reset functionality
    - User metadata management
    """

    def __init__(self, client: Client, config: SupabaseConfig):
        """
        Initialize authentication interface.

        Args:
            client: Supabase client instance
            config: Supabase configuration
        """
        self.client = client
        self.config = config
        self.current_user = None
        self.current_session = None

    async def register_user(
        self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Register a new user.

        Args:
            email: User email address
            password: User password
            metadata: Additional user metadata

        Returns:
            Tuple of (success, user_id, error_message)
        """
        try:
            # Register user with Supabase Auth
            response = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": metadata or {}},
                }
            )

            if response.user:
                user_id = response.user.id

                # Create user profile
                profile_data = {
                    "id": user_id,
                    "email": email,
                    "full_name": metadata.get("full_name") if metadata else None,
                    "avatar_url": metadata.get("avatar_url") if metadata else None,
                    "timezone": metadata.get("timezone", "UTC") if metadata else "UTC",
                    "language": metadata.get("language", "en") if metadata else "en",
                    "email_processing_enabled": True,
                    "plan_type": "free",
                    "email_quota_monthly": 1000,
                    "emails_processed_this_month": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                # Insert profile into profiles table
                self.client.table(self.config.TABLES["profiles"]).insert(
                    profile_data
                ).execute()

                return True, user_id, None
            else:
                return False, "", "User registration failed"

        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            return False, "", str(e)

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Tuple of (success, user_id, error_message)
        """
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if response.user and response.session:
                self.current_user = response.user
                self.current_session = response.session

                # Update last login timestamp
                self.client.table(self.config.TABLES["profiles"]).update(
                    {
                        "last_login_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", response.user.id).execute()

                return True, response.user.id, None
            else:
                return False, None, "Invalid credentials"

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False, None, str(e)

    async def logout_user(self) -> bool:
        """
        Logout current user.

        Returns:
            bool: Success status
        """
        try:
            self.client.auth.sign_out()
            self.current_user = None
            self.current_session = None
            return True
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user info.

        Returns:
            User data dictionary or None
        """
        try:
            if not self.current_user:
                # Try to get user from session
                user = self.client.auth.get_user()
                if user:
                    self.current_user = user
                else:
                    return None

            # Ensure we have a valid user before accessing properties
            if not self.current_user:
                return None

            # Get full user profile
            response = (
                self.client.table(self.config.TABLES["profiles"])
                .select("*")
                .eq("id", self.current_user.id)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get current user: {str(e)}")
            return None

    async def update_user_profile(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user profile.

        Args:
            user_id: User ID
            updates: Profile updates

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Add updated timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update profile
            self.client.table(self.config.TABLES["profiles"]).update(updates).eq(
                "id", user_id
            ).execute()

            return True, None

        except Exception as e:
            logger.error(f"Profile update failed: {str(e)}")
            return False, str(e)

    async def reset_password(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Send password reset email.

        Args:
            email: User email

        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.client.auth.reset_password_email(email)
            return True, None
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            return False, str(e)

    async def change_password(
        self, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.

        Args:
            current_password: Current password (must be verified before changing)
            new_password: New password

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not self.current_user:
                return False, "No authenticated user"

            # First verify the current password by attempting to re-authenticate
            email = self.current_user.email
            try:
                await self.authenticate_user(email, current_password)
            except Exception:  # noqa: E722
                return False, "Current password is incorrect"

            # Update to new password
            self.client.auth.update_user({"password": new_password})
            return True, None

        except Exception as e:
            logger.error(f"Password change failed: {str(e)}")
            return False, str(e)

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """
        Get current session info.

        Returns:
            Session data or None
        """
        if self.current_session:
            return {
                "access_token": self.current_session.access_token,
                "refresh_token": self.current_session.refresh_token,
                "expires_at": self.current_session.expires_at,
                "user_id": self.current_user.id if self.current_user else None,
            }
        return None

    async def refresh_session(self) -> Tuple[bool, Optional[str]]:
        """
        Refresh current session.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not self.current_session:
                return False, "No active session"

            response = self.client.auth.refresh_session(
                self.current_session.refresh_token
            )

            if response.session:
                self.current_session = response.session
                return True, None
            else:
                return False, "Session refresh failed"

        except Exception as e:
            logger.error(f"Session refresh failed: {str(e)}")
            return False, str(e)

    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated.

        Returns:
            bool: Authentication status
        """
        return self.current_user is not None and self.current_session is not None

    def get_user_id(self) -> Optional[str]:
        """
        Get current user ID.

        Returns:
            User ID or None
        """
        return self.current_user.id if self.current_user else None

    async def get_user_quota_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's email processing quota status.

        Args:
            user_id: User ID

        Returns:
            Quota status information
        """
        try:
            response = (
                self.client.table(self.config.TABLES["profiles"])
                .select("plan_type, email_quota_monthly, emails_processed_this_month")
                .eq("id", user_id)
                .execute()
            )

            if response.data:
                profile = response.data[0]
                quota_used = profile["emails_processed_this_month"]
                quota_limit = profile["email_quota_monthly"]

                return {
                    "plan_type": profile["plan_type"],
                    "quota_used": quota_used,
                    "quota_limit": quota_limit,
                    "quota_remaining": max(0, quota_limit - quota_used),
                    "quota_percentage": (
                        (quota_used / quota_limit * 100) if quota_limit > 0 else 0
                    ),
                }
            else:
                return {
                    "plan_type": "free",
                    "quota_used": 0,
                    "quota_limit": 1000,
                    "quota_remaining": 1000,
                    "quota_percentage": 0,
                }

        except Exception as e:
            logger.error(f"Failed to get quota status: {str(e)}")
            return {
                "plan_type": "free",
                "quota_used": 0,
                "quota_limit": 1000,
                "quota_remaining": 1000,
                "quota_percentage": 0,
                "error": str(e),
            }

    async def increment_email_count(self, user_id: str) -> bool:
        """
        Increment user's monthly email processing count.

        Args:
            user_id: User ID

        Returns:
            bool: Success status
        """
        try:
            # Use database function to safely increment
            self.client.rpc(
                "increment_user_email_count", {"user_id": user_id}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to increment email count: {str(e)}")
            return False
