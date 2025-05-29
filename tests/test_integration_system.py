#!/usr/bin/env python3
"""
Test the complete integration system end-to-end
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

from src.integrations import PluginManager
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Define example plugins inline for testing
class EmailCategoryPlugin:
    """Example plugin that categorizes emails"""

    def get_name(self) -> str:
        return "email-category-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> list:
        return []

    async def initialize(self, config: dict) -> None:
        """Initialize with categories"""
        self.categories = config.get(
            "categories", ["work", "personal", "marketing", "notifications", "support"]
        )
        print(f"EmailCategoryPlugin initialized with categories: {self.categories}")

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """Add category based on email content"""
        subject = email.email_data.subject.lower()
        from_email = email.email_data.from_email.lower()

        # Simple categorization logic
        if any(word in subject for word in ["urgent", "support", "help"]):
            category = "support"
        elif any(word in subject for word in ["work", "business", "server"]):
            category = "work"
        else:
            category = "personal"

        # Add category to tags
        email.analysis.tags.append(f"category:{category}")
        return email

    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        print("EmailCategoryPlugin cleaned up")


class SpamDetectionPlugin:
    """Example plugin that adds spam detection"""

    def get_name(self) -> str:
        return "spam-detection-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> list:
        return []

    async def initialize(self, config: dict) -> None:
        """Initialize spam detection"""
        self.spam_threshold = config.get("spam_threshold", 0.8)
        print(f"SpamDetectionPlugin initialized with threshold: {self.spam_threshold}")

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """Analyze for spam indicators"""
        spam_score = 0.0
        content = (
            email.email_data.subject + " " + (email.email_data.text_body or "")
        ).lower()

        # Simple spam detection
        spam_keywords = ["free", "winner", "urgent", "money"]
        for keyword in spam_keywords:
            if keyword in content:
                spam_score += 0.2

        # Add spam analysis to tags
        if spam_score > self.spam_threshold:
            email.analysis.tags.append("spam:likely")
        else:
            email.analysis.tags.append("spam:unlikely")

        return email

    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        print("SpamDetectionPlugin cleaned up")


async def test_integration_system():
    """Test the complete integration system"""
    print("🧪 Testing Complete Integration System")
    print("=" * 50)

    # Setup plugin manager
    plugin_manager = PluginManager()

    # Create and register plugins
    category_plugin = EmailCategoryPlugin()
    spam_plugin = SpamDetectionPlugin()

    await category_plugin.initialize({})
    await spam_plugin.initialize({"spam_threshold": 0.7})

    plugin_manager.register_plugin(category_plugin, priority=50)
    plugin_manager.register_plugin(spam_plugin, priority=60)

    print(f"✅ Registered {len(plugin_manager.plugins)} plugins")

    # Create test emails
    test_emails = [
        {
            "subject": "URGENT: Server down, need immediate help!",
            "from": "client@business.com",
            "text": "Our production server is down and we are losing money. Please help ASAP!",
        },
        {
            "subject": "FREE MONEY! You're a winner!",
            "from": "noreply@spam.com",
            "text": "Congratulations! You've won free money! Click here now!",
        },
        {
            "subject": "Meeting notes from today",
            "from": "colleague@company.com",
            "text": "Here are the notes from our team meeting today.",
        },
    ]

    results = []

    for i, email_info in enumerate(test_emails):
        # Create email data
        email_data = EmailData(
            message_id=f"test-{i + 1}",
            from_email=email_info["from"],
            to_emails=["recipient@company.com"],
            subject=email_info["subject"],
            text_body=email_info["text"],
            received_at=datetime.now(timezone.utc),
        )

        # Create analysis
        email_analysis = EmailAnalysis(
            urgency_score=50,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.8,
            keywords=[],
            action_items=[],
            temporal_references=[],
            tags=[],
        )

        # Create processed email
        processed_email = ProcessedEmail(
            id=str(uuid.uuid4()),
            email_data=email_data,
            analysis=email_analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(timezone.utc),
        )

        print(f"\n📧 Processing Email {i + 1}: {email_info['subject'][:50]}...")
        print(f"   Original tags: {processed_email.analysis.tags}")

        # Process through plugins
        enhanced_email = await plugin_manager.process_email_through_plugins(
            processed_email
        )

        print(f"   Enhanced tags: {enhanced_email.analysis.tags}")
        results.append(enhanced_email)

    print("\n🎯 Integration System Test Results:")
    print("=" * 50)
    for i, email in enumerate(results):
        print(f"Email {i + 1}: {email.email_data.subject[:40]}...")
        print(f"  Tags: {email.analysis.tags}")
        print()

    print("✅ Integration system test completed successfully!")
    return results


if __name__ == "__main__":
    asyncio.run(test_integration_system())
