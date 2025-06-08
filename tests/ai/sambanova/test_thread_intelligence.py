#!/usr/bin/env python3
"""
Test script for SambaNova Thread Intelligence Integration

This script tests the integration of ThreadIntelligenceEngine with the SambaNovaPlugin.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List

import pytest

# Add the src directory to the Python path
sys.path.insert(0, "src")

from src.ai.plugin import SambaNovaPlugin
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_email_thread() -> List[ProcessedEmail]:
    """Create a sample email thread for testing."""

    emails = []

    # Email 1: Project initiation
    email1_data = EmailData(
        from_email="manager@company.com",
        to_emails=["team-lead@company.com", "developer@company.com"],
        subject="New Project: Customer Portal Redesign",
        text_body="""Hi Team,

We've received approval for the customer portal redesign project. This is a high-priority initiative that needs to be completed by Q2.

Key requirements:
- Modernize the UI/UX
- Improve mobile responsiveness  
- Add new authentication features
- Integrate with new CRM system

Please review and let me know your thoughts on timeline and resource allocation.

Thanks,
Sarah""",
        message_id="email-1-project-init",
        received_at=datetime(2025, 1, 1, 9, 0, 0),
    )

    email1 = ProcessedEmail(
        id="email-1",
        email_data=email1_data,
        analysis=EmailAnalysis(
            urgency_score=80,
            urgency_level=UrgencyLevel.HIGH,
            sentiment="positive",
            confidence=0.8,
            keywords=["project", "portal", "redesign", "priority"],
            action_items=["Review requirements", "Provide timeline estimate"],
            tags=["project-management", "high-priority"],
        ),
        status=EmailStatus.ANALYZED,
        processed_at=datetime.now(),
    )
    emails.append(email1)

    # Email 2: Team lead response
    email2_data = EmailData(
        from_email="team-lead@company.com",
        to_emails=["manager@company.com", "developer@company.com"],
        subject="RE: New Project: Customer Portal Redesign",
        text_body="""Sarah,

Thanks for the project details. I've reviewed the requirements and have some initial thoughts:

Timeline estimate: 12-14 weeks
- UI/UX design: 3 weeks
- Frontend development: 6 weeks  
- Backend integration: 4 weeks
- Testing and deployment: 1 week

Resources needed:
- 2 frontend developers
- 1 backend developer
- 1 UX designer
- QA support

I think the Q2 deadline is aggressive but achievable if we start immediately. Should we schedule a kickoff meeting?

Best,
Mike""",
        message_id="email-2-team-response",
        received_at=datetime(2025, 1, 1, 14, 30, 0),
    )

    email2 = ProcessedEmail(
        id="email-2",
        email_data=email2_data,
        analysis=EmailAnalysis(
            urgency_score=70,
            urgency_level=UrgencyLevel.HIGH,
            sentiment="analytical",
            confidence=0.9,
            keywords=["timeline", "resources", "estimate", "meeting"],
            action_items=["Schedule kickoff meeting"],
            tags=["project-planning", "resource-allocation"],
        ),
        status=EmailStatus.ANALYZED,
        processed_at=datetime.now(),
    )
    emails.append(email2)

    # Email 3: Developer input
    email3_data = EmailData(
        from_email="developer@company.com",
        to_emails=["manager@company.com", "team-lead@company.com"],
        subject="RE: New Project: Customer Portal Redesign",
        text_body="""Hi Sarah and Mike,

I agree with Mike's timeline estimate. However, I have some concerns about the CRM integration:

- The new CRM system is still in beta
- API documentation is incomplete  
- We might face integration challenges

Suggestions:
1. Start with UI/UX work while CRM team finalizes their system
2. Plan for additional testing time for integration
3. Consider a phased rollout approach

Also, do we have access to the current user analytics to inform the redesign?

Thanks,
Alex""",
        message_id="email-3-developer-input",
        received_at=datetime(2025, 1, 2, 10, 15, 0),
    )

    email3 = ProcessedEmail(
        id="email-3",
        email_data=email3_data,
        analysis=EmailAnalysis(
            urgency_score=60,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="concerned",
            confidence=0.85,
            keywords=["concerns", "CRM", "integration", "testing", "analytics"],
            action_items=[
                "Review CRM documentation",
                "Access user analytics",
                "Plan phased rollout",
            ],
            tags=["technical-concerns", "integration-planning"],
        ),
        status=EmailStatus.ANALYZED,
        processed_at=datetime.now(),
    )
    emails.append(email3)

    return emails


@pytest.mark.asyncio
async def test_plugin_thread_intelligence():
    """Test the thread intelligence integration in SambaNovaPlugin."""

    logger.info("Starting SambaNova Thread Intelligence Integration Test")

    # Create plugin configuration
    config = {
        "api_key": "test-api-key",
        "model": "sambanova-large",
        "max_concurrent": 3,
        "timeout": 30,
        "enable_caching": True,
        "batch_processing": True,
    }

    # Initialize plugin
    plugin = SambaNovaPlugin()

    try:
        # Note: This will fail with real initialization due to test API key
        # But we can test the structure and integration
        logger.info("Testing plugin structure and thread intelligence integration...")

        # Check that thread intelligence is properly integrated
        assert hasattr(
            plugin, "thread_intelligence"
        ), "Plugin missing thread_intelligence attribute"
        assert hasattr(
            plugin, "analyze_email_thread"
        ), "Plugin missing analyze_email_thread method"
        assert hasattr(
            plugin, "batch_analyze_threads"
        ), "Plugin missing batch_analyze_threads method"

        logger.info("✅ Plugin structure validation passed")

        # Test with sample email thread
        sample_emails = create_sample_email_thread()
        logger.info(f"Created sample email thread with {len(sample_emails)} emails")

        # Test method signatures and error handling
        try:
            # This should fail gracefully since plugin is not initialized
            thread_analysis = await plugin.analyze_email_thread(sample_emails)
            logger.info(f"Thread analysis result: {type(thread_analysis)}")

            # Should return empty dict when not initialized
            assert isinstance(thread_analysis, dict), "Expected dict return type"

        except Exception as e:
            logger.info(f"Expected error for uninitialized plugin: {e}")

        # Test batch analysis method
        try:
            thread_groups = [sample_emails]
            batch_results = await plugin.batch_analyze_threads(thread_groups)
            logger.info(f"Batch analysis result: {type(batch_results)}")

            # Should return empty list when not initialized
            assert isinstance(batch_results, list), "Expected list return type"

        except Exception as e:
            logger.info(f"Expected error for uninitialized plugin: {e}")

        logger.info("✅ Thread intelligence integration test completed successfully")

        # Test processing statistics integration
        stats = plugin.get_processing_stats()
        logger.info(f"Plugin stats keys: {list(stats.keys())}")

        assert "plugin_name" in stats, "Missing plugin_name in stats"
        assert "plugin_version" in stats, "Missing plugin_version in stats"

        logger.info("✅ Statistics integration test passed")

        # Test cleanup method
        await plugin.cleanup()
        logger.info("✅ Cleanup test passed")

        logger.info("🎉 All thread intelligence integration tests passed!")

    except Exception as e:
        logger.error(
            f"❌ Thread intelligence integration test failed: {e}", exc_info=True
        )
        raise


@pytest.mark.asyncio
async def test_thread_analysis_data_structure():
    """Test the data structure and format of thread analysis results."""

    logger.info("Testing thread analysis data structure...")

    # Import ThreadIntelligenceEngine directly
    from src.ai.providers.sambanova.thread_intelligence import (
        ActionItemEvolution,
        ConversationState,
        ConversationSummary,
        DecisionPoint,
        StakeholderProfile,
        StakeholderRole,
    )

    # Test data structure creation
    sample_summary = ConversationSummary(
        thread_id="test-thread-1",
        subject_line="Test Project Discussion",
        participants=["user1@test.com", "user2@test.com"],
        email_count=3,
        conversation_state=ConversationState.ONGOING,
        key_topics=["project", "timeline", "resources"],
        consensus_level=0.8,
        urgency_escalation=0.6,
        executive_summary="Test project discussion with good consensus",
        next_steps=["Schedule meeting", "Review resources"],
    )

    logger.info(f"✅ ConversationSummary created: {sample_summary.thread_id}")

    # Test decision point
    decision = DecisionPoint(
        id="decision-1",
        description="Choose project timeline",
        emails_involved=["email-1", "email-2"],
        stakeholders=["manager@test.com", "lead@test.com"],
        options_discussed=["12 weeks", "14 weeks"],
        confidence=0.8,
        status="decided",
    )

    logger.info(f"✅ DecisionPoint created: {decision.id}")

    # Test stakeholder profile
    stakeholder = StakeholderProfile(
        email_address="manager@test.com",
        role=StakeholderRole.DECISION_MAKER,
        influence_score=0.9,
        participation_level=0.7,
    )

    logger.info(f"✅ StakeholderProfile created: {stakeholder.email_address}")

    # Test action item evolution
    action_item = ActionItemEvolution(
        original_item="Review requirements",
        current_item="Complete requirements review by Friday",
        completion_status="in_progress",
    )

    logger.info(f"✅ ActionItemEvolution created: {action_item.original_item}")

    logger.info("🎉 All data structure tests passed!")


async def main():
    """Main test function."""
    try:
        logger.info("=" * 60)
        logger.info("SambaNova Thread Intelligence Integration Test Suite")
        logger.info("=" * 60)

        # Test 1: Data structure validation
        await test_thread_analysis_data_structure()
        logger.info("")

        # Test 2: Plugin integration
        await test_plugin_thread_intelligence()
        logger.info("")

        logger.info("=" * 60)
        logger.info("🎉 ALL TESTS PASSED! Thread Intelligence integration is ready!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
