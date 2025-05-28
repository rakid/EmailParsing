"""
Pytest configuration and shared fixtures for unit tests
"""
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configure pytest asyncio
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    """Configure pytest settings"""
    # Set asyncio event loop scope to function to avoid warnings
    config.option.asyncio_default_fixture_loop_scope = "function"

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def sample_email_data():
    """Sample email data for testing with correct field names for EmailData model"""
    return {
        "message_id": "test-message-123@example.com",
        "from_email": "john.doe@example.com",
        "to_emails": ["jane.smith@company.com"], 
        "subject": "URGENT: Project deadline tomorrow - need your input ASAP",
        "text_body": """
Hi Jane,

I hope this email finds you well. I wanted to reach out regarding the Q4 marketing campaign project that we discussed last week.

URGENT TASKS:
1. Review the budget proposal by tomorrow 5 PM
2. Schedule meeting with stakeholders for Friday
3. Submit final report to management

The deadline is tomorrow and I'm getting quite stressed about this. Can you please prioritize this? The client is breathing down our necks and we really need to deliver.

Please let me know if you can help with this ASAP.

Best regards,
John

P.S. - Also, can you call me at 555-123-4567 when you get this?
        """,
        "html_body": """
<html>
<body>
<p>Hi Jane,</p>
<p>I hope this email finds you well. I wanted to reach out regarding the Q4 marketing campaign project that we discussed last week.</p>
<p><strong>URGENT TASKS:</strong></p>
<ol>
<li>Review the budget proposal by tomorrow 5 PM</li>
<li>Schedule meeting with stakeholders for Friday</li>
<li>Submit final report to management</li>
</ol>
<p>The deadline is tomorrow and I'm getting quite <em>stressed</em> about this. Can you please prioritize this? The client is breathing down our necks and we really need to deliver.</p>
<p>Please let me know if you can help with this ASAP.</p>
<p>Best regards,<br>John</p>
<p>P.S. - Also, can you call me at 555-123-4567 when you get this?</p>
</body>
</html>
        """,
        "received_at": datetime(2025, 5, 27, 14, 30, 0),
        "cc_emails": [],
        "bcc_emails": [],
        "attachments": [],
        "headers": {}
    }

@pytest.fixture  
def sample_low_urgency_email():
    """Low urgency email for testing"""
    return {
        "message_id": "newsletter-456@company.com",
        "from_email": "newsletter@company.com",
        "to_emails": ["subscriber@example.com"],
        "subject": "Weekly Newsletter - Industry Updates",
        "text_body": """
Hello,

Hope you're having a great week! Here are some interesting industry updates:

- New trends in email marketing
- Best practices for customer engagement  
- Upcoming industry conferences

Feel free to read when you have time. No rush on this one.

Cheers,
Marketing Team
        """,
        "received_at": datetime(2025, 5, 27, 10, 0, 0),
        "cc_emails": [],
        "bcc_emails": [],
        "attachments": [],
        "headers": {}
    }

@pytest.fixture
def sample_positive_email():
    """Positive sentiment email for testing"""
    return {
        "message_id": "celebration-789@startup.com",
        "from_email": "team@startup.com",
        "to_emails": ["all@startup.com"],
        "subject": "Congratulations! We hit our quarterly targets!",
        "text_body": """
Dear Team,

I'm thrilled to announce that we've exceeded our Q1 targets by 15%! This is fantastic news and a testament to everyone's hard work.

Great job everyone! Let's celebrate this achievement. Team lunch on Friday!

Best,
CEO
        """,
        "received_at": datetime(2025, 5, 27, 16, 0, 0),
        "cc_emails": [],
        "bcc_emails": [],
        "attachments": [],
        "headers": {}
    }

@pytest.fixture
def sample_email_with_tasks():
    """Email containing multiple actionable tasks"""
    return {
        "message_id": "sprint-actions-101@corp.com",
        "from_email": "project.manager@corp.com",
        "to_emails": ["dev.team@corp.com"],
        "subject": "Action Items from Sprint Planning",
        "text_body": """
Team,

Following up on our sprint planning meeting. Here are the action items:

ACTION REQUIRED:
- Fix the login bug by Wednesday
- Update the user documentation 
- Deploy to staging environment by Friday
- Review pull requests from last week
- Schedule client demo for next Tuesday

Please confirm receipt and let me know if you have any questions.

Thanks,
PM
        """,
        "received_at": datetime(2025, 5, 27, 11, 0, 0),
        "cc_emails": [],
        "bcc_emails": [],
        "attachments": [],
        "headers": {}
    }

@pytest.fixture
def sample_analysis_data():
    """Sample email analysis data for testing"""
    return {
        "urgency_score": 75,
        "urgency_level": "high",
        "sentiment": "negative",
        "confidence": 0.85,
        "keywords": ["urgent", "deadline", "ASAP", "stressed", "prioritize"],
        "action_items": [
            "Review the budget proposal by tomorrow 5 PM",
            "Schedule meeting with stakeholders for Friday", 
            "Submit final report to management",
            "Call John at 555-123-4567"
        ],
        "temporal_references": ["tomorrow", "5 PM", "Friday"],
        "tags": ["urgent", "project", "deadline", "budget"]
    }

@pytest.fixture  
def sample_postmark_payload():
    """Sample Postmark webhook payload for testing"""
    return {
        "From": "john.doe@example.com",
        "To": "jane.smith@company.com",
        "ToFull": [{"Email": "jane.smith@company.com", "Name": "Jane Smith"}],
        "Cc": "",
        "Bcc": "",
        "Subject": "URGENT: Project deadline tomorrow - need your input ASAP",
        "Tag": "urgent",
        "HtmlBody": """
<html>
<body>
<p>Hi Jane,</p>
<p>I hope this email finds you well. I wanted to reach out regarding the Q4 marketing campaign project that we discussed last week.</p>
<p><strong>URGENT TASKS:</strong></p>
<ol>
<li>Review the budget proposal by tomorrow 5 PM</li>
<li>Schedule meeting with stakeholders for Friday</li>
<li>Submit final report to management</li>
</ol>
<p>The deadline is tomorrow and I'm getting quite <em>stressed</em> about this. Can you please prioritize this? The client is breathing down our necks and we really need to deliver.</p>
<p>Please let me know if you can help with this ASAP.</p>
<p>Best regards,<br>John</p>
<p>P.S. - Also, can you call me at 555-123-4567 when you get this?</p>
</body>
</html>
        """,
        "TextBody": """
Hi Jane,

I hope this email finds you well. I wanted to reach out regarding the Q4 marketing campaign project that we discussed last week.

URGENT TASKS:
1. Review the budget proposal by tomorrow 5 PM
2. Schedule meeting with stakeholders for Friday
3. Submit final report to management

The deadline is tomorrow and I'm getting quite stressed about this. Can you please prioritize this? The client is breathing down our necks and we really need to deliver.

Please let me know if you can help with this ASAP.

Best regards,
John

P.S. - Also, can you call me at 555-123-4567 when you get this?
        """,
        "ReplyTo": "john.doe@example.com",
        "Date": "2025-05-27T14:30:00.000Z",
        "MessageID": "test-message-123@example.com",
        "Headers": [
            {"Name": "X-Priority", "Value": "1"},
            {"Name": "X-Mailer", "Value": "Outlook Express 6.00.2900.5512"}
        ],
        "Attachments": []
    }

@pytest.fixture
def clean_storage():
    """Clean email storage for testing - must be explicitly used by tests"""
    import storage
    from models import EmailStats
    # Clear global storage
    print(f"CONFTEST: Cleaning storage, current length: {len(storage.email_storage)}")
    storage.email_storage.clear()
    storage.stats.total_processed = 0
    storage.stats.total_errors = 0
    storage.stats.avg_urgency_score = 0.0
    storage.stats.last_processed = None
    storage.stats.processing_times.clear()
    print(f"CONFTEST: Storage cleaned, new length: {len(storage.email_storage)}")
    return storage.email_storage

@pytest.fixture
def sample_email_model():
    """Sample EmailData model for testing"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from models import EmailData
    return EmailData(
        message_id="test-123",
        from_email="test@example.com",
        to_emails=["recipient@example.com"],
        subject="Test Email",
        text_body="This is a test email",
        html_body="<p>This is a test email</p>",
        received_at=datetime.now(),
        attachments=[]
    )

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_postmark_webhook():
    """Mock Postmark webhook payload"""
    return {
        "From": "sender@example.com",
        "To": "recipient@example.com", 
        "Cc": "",
        "Bcc": "",
        "Subject": "Test Email Subject",
        "Tag": "test",
        "HtmlBody": "<p>This is a test email with <strong>HTML</strong> content.</p>",
        "TextBody": "This is a test email with plain text content.",
        "ReplyTo": "noreply@example.com",
        "Date": "2025-05-27T15:30:00.000Z",
        "MessageID": "b7bc2f4a-e38e-4336-af7d-e87c17c4b0c5"
    }

@pytest.fixture
def edge_case_emails():
    """Collection of edge case emails for robust testing"""
    return [
        {
            "name": "empty_content",
            "data": {
                "message_id": "empty-123",
                "from_email": "empty@test.com",
                "to_emails": ["user@test.com"],
                "subject": "",
                "text_body": "",
                "received_at": datetime(2025, 5, 27, 12, 0, 0),
                "cc_emails": [],
                "bcc_emails": [],
                "attachments": [],
                "headers": {}
            }
        },
        {
            "name": "very_long_content", 
            "data": {
                "message_id": "long-456",
                "from_email": "long@test.com",
                "to_emails": ["user@test.com"],
                "subject": "Very Long Email Content Test",
                "text_body": "This is a test email. " * 1000,  # Very long content
                "received_at": datetime(2025, 5, 27, 12, 0, 0),
                "cc_emails": [],
                "bcc_emails": [],
                "attachments": [],
                "headers": {}
            }
        },
        {
            "name": "special_characters",
            "data": {
                "message_id": "special-789",
                "from_email": "special@test.com",
                "to_emails": ["user@test.com"], 
                "subject": "Spéciål Chåràctërs Tëst 🎉 中文 العربية",
                "text_body": "Email with émojis 🚀💡 and spëciål chäräctërs ñoño",
                "received_at": datetime(2025, 5, 27, 12, 0, 0),
                "cc_emails": [],
                "bcc_emails": [],
                "attachments": [],
                "headers": {}
            }
        },
        {
            "name": "malformed_data",
            "data": {
                "message_id": "malformed-101",
                "from_email": "malformed",  # Missing domain
                "to_emails": [],  # Empty recipient
                "subject": "",  # Empty subject instead of None
                "text_body": "12345",  # String content
                "received_at": datetime(2025, 5, 27, 12, 0, 0),  # Valid date
                "cc_emails": [],
                "bcc_emails": [],
                "attachments": [],
                "headers": {}
            }
        }
    ]

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "edge_case: mark test as edge case scenario"
    )
