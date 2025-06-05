"""
Test suite for SupabaseDatabaseInterface.

This module contains comprehensive tests for the Supabase database interface,
covering database operations, email storage, and data retrieval.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from src.models import (
    AttachmentData,
    EmailAnalysis,
    EmailData,
    EmailStats,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)
from src.supabase_integration.config import SupabaseConfig
from src.supabase_integration.database_interface import (
    DB_NOT_CONNECTED_ERROR,
    SupabaseDatabaseInterface,
)


@pytest.fixture
def mock_supabase_config():
    """Create a mock Supabase configuration."""
    config = MagicMock(spec=SupabaseConfig)
    config.supabase_url = "https://test.supabase.co"
    config.supabase_key = "test-key"
    config.TABLES = {
        "emails": "emails",
        "email_analysis": "email_analysis",
        "email_attachments": "email_attachments",
        "tasks": "tasks",
        "user_profiles": "user_profiles",
    }
    config.is_configured.return_value = True
    return config


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client for testing."""
    client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_table.select = MagicMock()
    mock_table.insert = MagicMock()
    mock_table.upsert = MagicMock()
    mock_table.update = MagicMock()
    mock_table.delete = MagicMock()

    # Chain method calls
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.gte = MagicMock(return_value=mock_table)
    mock_table.lte = MagicMock(return_value=mock_table)
    mock_table.limit = MagicMock(return_value=mock_table)
    mock_table.order = MagicMock(return_value=mock_table)
    mock_table.on_conflict = MagicMock(return_value=mock_table)

    # Mock execute responses
    mock_response = MagicMock()
    mock_response.data = []
    mock_table.execute = MagicMock(return_value=mock_response)

    client.table = MagicMock(return_value=mock_table)
    return client


@pytest.fixture
def sample_processed_email():
    """Create a sample ProcessedEmail for testing."""
    email_data = EmailData(
        message_id="test-message-id",
        subject="Test Subject",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        text_body="Test email body",
        received_at=datetime.now(timezone.utc),
    )

    analysis = EmailAnalysis(
        sentiment="positive",
        category="business",
        action_items=["Follow up with client"],
        urgency_score=70,
        urgency_level="medium",
        confidence=0.85,
    )

    return ProcessedEmail(
        id="test-email-id",
        email_data=email_data,
        analysis=analysis,
        processing_timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_email_data():
    """Create sample EmailData for testing."""
    return EmailData(
        message_id="test-msg-id",
        subject="Test Email",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        text_body="Test email body",
        received_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_analysis():
    """Create sample EmailAnalysis for testing."""
    return EmailAnalysis(
        sentiment="positive",
        category="business",
        action_items=["Follow up"],
        urgency_score=70,
        urgency_level="medium",
        confidence=0.85,
    )


@pytest.fixture
def database_interface(mock_supabase_config):
    """Create a SupabaseDatabaseInterface instance for testing."""
    return SupabaseDatabaseInterface(mock_supabase_config)


class TestSupabaseDatabaseInterface:
    """Test suite for SupabaseDatabaseInterface."""


@pytest.mark.asyncio
async def test_connect_success(database_interface, mock_supabase_config):
    """Test successful database connection."""
    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create:
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        await database_interface.connect()

        assert database_interface._connected is True
        assert database_interface.client is not None
        mock_create.assert_called_once_with(
            mock_supabase_config.supabase_url, mock_supabase_config.supabase_key
        )


@pytest.mark.asyncio
async def test_connect_failure_not_configured(database_interface, mock_supabase_config):
    """Test connection failure when not configured."""
    mock_supabase_config.is_configured.return_value = False

    with pytest.raises(ConnectionError, match="Supabase URL and API key are required"):
        await database_interface.connect()


@pytest.mark.asyncio
async def test_connect_failure_client_creation(
    database_interface, mock_supabase_config
):
    """Test connection failure during client creation."""
    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create:
        mock_create.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError, match="Failed to connect to Supabase"):
            await database_interface.connect()


@pytest.mark.asyncio
async def test_store_email_success(
    database_interface, mock_supabase_client, sample_processed_email
):
    """Test successful email storage."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    # Mock successful email insert
    mock_email_response = MagicMock()
    mock_email_response.data = [{"id": "stored-email-id"}]

    # Mock successful analysis insert
    mock_analysis_response = MagicMock()
    mock_analysis_response.data = [{"id": "analysis-id"}]

    # Set up the mock to return different responses for different operations
    def mock_table_calls(table_name):
        table_mock = MagicMock()
        if table_name == "emails":
            table_mock.upsert.return_value.execute.return_value = mock_email_response
        elif table_name == "email_analysis":
            table_mock.insert.return_value.execute.return_value = mock_analysis_response
        return table_mock

    mock_supabase_client.table.side_effect = mock_table_calls

    email_id = await database_interface.store_email(sample_processed_email)

    assert email_id == "stored-email-id"
    assert (
        mock_supabase_client.table.call_count >= 2
    )  # Called for both emails and analysis


@pytest.mark.asyncio
async def test_store_email_not_connected(database_interface, sample_processed_email):
    """Test email storage when not connected."""
    database_interface._connected = False

    with pytest.raises(RuntimeError, match="Database not connected"):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_store_email_failure(
    database_interface, mock_supabase_client, sample_processed_email
):
    """Test email storage failure."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    mock_supabase_client.table.return_value.upsert.return_value.execute.side_effect = (
        Exception("Storage failed")
    )

    with pytest.raises(Exception, match="Storage failed"):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_get_emails_success(database_interface, mock_supabase_client):
    """Test successful email retrieval."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    # Mock email data response
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "email-1",
            "message_id": "msg-1",
            "subject": "Test Subject 1",
            "from_email": "sender1@example.com",
            "to_emails": ["recipient@example.com"],
            "cc_emails": [],
            "bcc_emails": [],
            "text_body": "Test body 1",
            "html_body": None,
            "received_at": "2023-01-01T00:00:00Z",
            "headers": {},
            "status": "analyzed",
            "processed_at": "2023-01-01T00:00:01Z",
            "error_message": None,
            "webhook_payload": {},
            "email_attachments": [],
            "email_analysis": [],
        }
    ]
    # Setup mock table and method chain
    mock_table = mock_supabase_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_order = mock_eq.order.return_value
    mock_order.execute.return_value = mock_response

    emails = await database_interface.get_emails()

    assert len(emails) == 1
    assert emails[0].id == "email-1"
    assert emails[0].email_data.subject == "Test Subject 1"


@pytest.mark.asyncio
async def test_get_emails_with_filters(database_interface, mock_supabase_client):
    """Test email retrieval with filters."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    # Setup mock response and method chain
    mock_response = MagicMock()
    mock_response.data = []

    # Setup mock table and method chain
    mock_table = mock_supabase_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_gte = mock_eq.gte.return_value
    mock_lte = mock_gte.lte.return_value
    mock_order = mock_lte.order.return_value
    mock_order.execute.return_value = mock_response

    filters = {
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
        "sender": "test@example.com",
    }

    emails = await database_interface.get_emails(filters=filters)

    assert isinstance(emails, list)


@pytest.mark.asyncio
async def test_get_email_by_id_success(database_interface, mock_supabase_client):
    """Test successful email retrieval by ID."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "email-1",
            "message_id": "msg-1",
            "subject": "Test Subject",
            "from_email": "sender@example.com",
            "to_emails": ["recipient@example.com"],
            "cc_emails": [],
            "bcc_emails": [],
            "text_body": "Test body",
            "html_body": None,
            "received_at": "2023-01-01T00:00:00Z",
            "headers": {},
            "status": "analyzed",
            "processed_at": "2023-01-01T00:00:01Z",
            "error_message": None,
            "webhook_payload": {},
            "email_attachments": [],
            "email_analysis": [],
        }
    ]
    mock_table = mock_supabase_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_eq.execute.return_value = mock_response

    email = await database_interface.get_email_by_id("email-1")

    assert email is not None
    assert email.id == "email-1"


@pytest.mark.asyncio
async def test_get_email_by_id_not_found(database_interface, mock_supabase_client):
    """Test email retrieval by ID when not found."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    mock_response = MagicMock()
    mock_response.data = []
    mock_table = mock_supabase_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_eq.execute.return_value = mock_response

    email = await database_interface.get_email_by_id("nonexistent-id")

    assert email is None


@pytest.mark.asyncio
async def test_update_email_analysis_success(database_interface, mock_supabase_client):
    """Test successful email analysis update."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    mock_response = MagicMock()
    mock_response.data = [{"id": "analysis-id"}]
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    new_analysis = EmailAnalysis(
        sentiment="negative",
        category="urgent",
        action_items=["Immediate response required"],
        urgency_score=90,
        urgency_level="high",
        confidence=0.9,
    )

    success = await database_interface.update_email_analysis("email-1", new_analysis)

    assert success is True


@pytest.mark.asyncio
async def test_delete_email_success(database_interface, mock_supabase_client):
    """Test successful email deletion."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    mock_response = MagicMock()
    mock_response.data = [{"id": "email-1"}]
    mock_table = mock_supabase_client.table.return_value
    mock_delete = mock_table.delete.return_value
    mock_eq = mock_delete.eq.return_value
    mock_eq.execute.return_value = mock_response

    success = await database_interface.delete_email("email-1")

    assert success is True


@pytest.mark.asyncio
async def test_get_email_stats_success(database_interface, mock_supabase_client):
    """Test successful email statistics retrieval."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-id"

    # Mock count response
    mock_count_response = MagicMock()
    mock_count_response.count = 100

    mock_table = mock_supabase_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_gte = mock_eq.gte.return_value
    mock_lte = mock_gte.lte.return_value
    mock_order = mock_lte.order.return_value

    mock_order.execute.return_value = mock_count_response

    stats = await database_interface.get_email_stats()

    assert isinstance(stats, EmailStats)
    assert stats.total_processed >= 0


@pytest.mark.asyncio
async def test_disconnect_success(database_interface):
    """Test successful database disconnection."""
    database_interface._connected = True
    database_interface.client = MagicMock()

    await database_interface.disconnect()

    assert database_interface._connected is False
    assert database_interface.client is None


@pytest.mark.asyncio
async def test_get_emails_not_connected(database_interface):
    """Test email retrieval when not connected."""
    database_interface._connected = False

    with pytest.raises(RuntimeError, match="Database not connected"):
        await database_interface.get_emails()


@pytest.mark.asyncio
async def test_set_current_user_id(database_interface):
    """Test setting current user ID."""
    user_id = "test-user-123"
    database_interface.set_current_user_id(user_id)

    assert database_interface.current_user_id == user_id


@pytest.mark.asyncio
async def test_processed_email_to_supabase_conversion(
    database_interface, sample_processed_email
):
    """Test conversion of ProcessedEmail to Supabase format."""
    database_interface.current_user_id = "test-user-id"

    # Access the private method for testing
    result = database_interface._processed_email_to_supabase(sample_processed_email)

    assert result["message_id"] == sample_processed_email.email_data.message_id
    assert result["subject"] == sample_processed_email.email_data.subject
    assert result["from_email"] == sample_processed_email.email_data.from_email
    assert result["user_id"] == "test-user-id"


@pytest.mark.asyncio
async def test_supabase_to_processed_email_conversion(database_interface):
    """Test conversion from Supabase format to ProcessedEmail."""
    supabase_data = {
        "id": "email-1",
        "message_id": "msg-1",
        "subject": "Test Subject",
        "from_email": "sender@example.com",
        "to_emails": ["recipient@example.com"],
        "cc_emails": [],
        "bcc_emails": [],
        "text_body": "Test body",
        "html_body": None,
        "received_at": "2023-01-01T00:00:00+00:00",
        "headers": {},
        "status": "analyzed",
        "processed_at": "2023-01-01T00:00:01+00:00",
        "error_message": None,
        "webhook_payload": {},
        "email_attachments": [],
        "email_analysis": [],
    }

    # Access the private method for testing
    result = database_interface._supabase_to_processed_email(supabase_data)

    assert result.id == "email-1"
    assert result.email_data.subject == "Test Subject"
    assert result.email_data.from_email == "sender@example.com"


@pytest.mark.asyncio
async def test_batch_operations(database_interface, mock_supabase_client):
    """Test batch operations for multiple emails."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    # Create multiple sample emails
    emails = []
    for i in range(3):
        email_data = EmailData(
            message_id=f"test-message-{i}",
            subject=f"Test Subject {i}",
            from_email=f"sender{i}@example.com",
            to_emails=[f"recipient{i}@example.com"],
            text_body=f"Test email body {i}",
            received_at=datetime.now(timezone.utc),
        )

        analysis = EmailAnalysis(
            sentiment="neutral",
            category="general",
            action_items=[],
            urgency_score=50,
            urgency_level="medium",
            confidence=0.8,
        )

        emails.append(
            ProcessedEmail(
                id=f"test-email-{i}",
                email_data=email_data,
                analysis=analysis,
                processing_timestamp=datetime.now(timezone.utc),
            )
        )

    # Mock successful batch insert
    mock_response = MagicMock()
    mock_response.data = [{"id": f"stored-email-{i}"} for i in range(3)]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = (
        mock_response
    )

    # Test batch storage
    for email in emails:
        email_id = await database_interface.store_email(email)
        assert email_id is not None


@pytest.mark.asyncio
async def test_error_handling_edge_cases(database_interface, mock_supabase_client):
    """Test error handling for edge cases."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    # Test with invalid email data
    with pytest.raises(Exception):
        await database_interface.store_email(None)

    # Test get_email_by_id with empty string
    email = await database_interface.get_email_by_id("")
    assert email is None

    # Test operations when user_id is not set
    database_interface.current_user_id = None
    with pytest.raises(Exception):
        await database_interface.get_emails()


@pytest.mark.asyncio
async def test_real_time_subscription_management(
    database_interface, mock_supabase_client
):
    """Test real-time subscription management."""
    database_interface.client = mock_supabase_client
    database_interface._connected = True

    # Define a no-op callback function
    def noop_callback(data):
        pass

    # Test subscription creation
    subscription_id = database_interface.subscribe_to_changes(noop_callback)

    assert subscription_id in database_interface._real_time_subscriptions

    # Test unsubscription
    database_interface.unsubscribe_from_changes(subscription_id)

    assert subscription_id not in database_interface._real_time_subscriptions


@pytest.mark.asyncio
async def test_connection_string_override(database_interface):
    """Test connection with custom connection string."""
    custom_connection = "postgresql://custom:connection@localhost/db"

    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        await database_interface.connect(custom_connection)

        # Should still use the config URL and key, not the connection string
        # (as Supabase uses URL + key, not PostgreSQL connection strings)
        assert database_interface._connected is True


# =============================================================================
# COMPREHENSIVE TESTS - Additional coverage for error paths and edge cases
# =============================================================================


@pytest.mark.asyncio
async def test_connect_with_connection_string_override(
    database_interface, mock_supabase_config
):
    """Test connect with connection string override."""
    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create_client:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Use custom connection string (should parse URL from it)
        custom_connection = "supabase://custom.supabase.co"
        await database_interface.connect(custom_connection)

        # Should be connected with custom config
        assert database_interface._connected is True
        assert database_interface.client is mock_client


@pytest.mark.asyncio
async def test_connect_failure_invalid_config(database_interface):
    """Test connect failure with invalid config."""
    # Set invalid config
    database_interface.config.is_configured.return_value = False

    with pytest.raises(Exception, match="Supabase URL and API key are required"):
        await database_interface.connect()

    assert database_interface._connected is False


@pytest.mark.asyncio
async def test_connect_client_creation_failure_comprehensive(database_interface):
    """Test connect failure during client creation."""
    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create_client:
        mock_create_client.side_effect = Exception("Client creation failed")

        with pytest.raises(Exception, match="Failed to connect to Supabase"):
            await database_interface.connect()

    assert database_interface._connected is False


# =============================================================================
# COMPREHENSIVE STORAGE TESTS - Testing uncovered storage paths
# =============================================================================


@pytest.mark.asyncio
async def test_store_email_not_connected_comprehensive(
    database_interface, sample_processed_email
):
    """Test store_email when not connected."""
    # Ensure not connected
    database_interface._connected = False

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_store_email_with_attachments_comprehensive(
    database_interface, sample_email_data, sample_analysis
):
    """Test storing email with attachments."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Create email with attachments
    attachment = AttachmentData(
        name="test.pdf", content_type="application/pdf", size=1024
    )
    email_data_with_attachment = EmailData(
        message_id="attach-test@example.com",
        subject="Email with attachment",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        text_body="Email with attachment",
        received_at=datetime.now(timezone.utc),
        attachments=[attachment],
    )

    processed_email = ProcessedEmail(
        id="attach-email-id",
        email_data=email_data_with_attachment,
        analysis=sample_analysis,
        status=EmailStatus.ANALYZED,
    )

    # Mock successful storage response for both emails and attachments
    mock_response = MagicMock()
    mock_response.data = [{"id": "stored-email-id"}]

    # Setup mock to handle both email and attachment table calls
    def mock_table_side_effect(table_name):
        mock_table = MagicMock()
        mock_table.upsert.return_value.execute.return_value = mock_response
        mock_table.insert.return_value.execute.return_value = mock_response
        return mock_table

    mock_client.table.side_effect = mock_table_side_effect

    result = await database_interface.store_email(processed_email)

    assert result == "stored-email-id"
    # Verify both email and attachment tables were called
    assert mock_client.table.call_count >= 1


@pytest.mark.asyncio
async def test_store_email_database_error_comprehensive(
    database_interface, sample_processed_email
):
    """Test store_email with database error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock database error
    mock_client.table.return_value.upsert.return_value.execute.side_effect = APIError(
        {"message": "Database error", "details": "Upsert failed"}
    )

    with pytest.raises(Exception):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_store_email_empty_response_comprehensive(
    database_interface, sample_processed_email
):
    """Test store_email with empty response from database."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock empty response
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.table.return_value.upsert.return_value.execute.return_value = (
        mock_response
    )

    with pytest.raises(Exception, match="Failed to store email"):
        await database_interface.store_email(sample_processed_email)


# =============================================================================
# COMPREHENSIVE RETRIEVAL TESTS - Testing uncovered retrieval paths
# =============================================================================


@pytest.mark.asyncio
async def test_get_email_not_connected_comprehensive(database_interface):
    """Test get_email when not connected."""
    database_interface._connected = False

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.get_email("test-id")


@pytest.mark.asyncio
async def test_get_email_api_error_comprehensive(database_interface):
    """Test get_email with API error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock API error
    mock_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = APIError(
        {"message": "API error", "details": "Select failed"}
    )

    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.get_email("test-id")


@pytest.mark.asyncio
async def test_get_email_conversion_error_comprehensive(database_interface):
    """Test get_email with data conversion error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock response with invalid data (missing required fields)
    mock_response = MagicMock()
    mock_response.data = [{"invalid": "data"}]  # Missing required fields
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    with pytest.raises(RuntimeError, match="Failed to retrieve email"):
        await database_interface.get_email("test-id")


# =============================================================================
# COMPREHENSIVE SEARCH TESTS - Testing uncovered search paths
# =============================================================================


@pytest.mark.asyncio
async def test_search_emails_not_connected_comprehensive(database_interface):
    """Test search_emails when not connected."""
    database_interface._connected = False

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.search_emails({"urgency": "high"})


@pytest.mark.asyncio
async def test_search_emails_with_complex_filters_comprehensive(database_interface):
    """Test search_emails with complex filter combinations."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock response
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.table.return_value.select.return_value.execute.return_value = (
        mock_response
    )

    complex_filters = {
        "urgency": "high",
        "status": "analyzed",
        "from_email": "important@company.com",
        "subject_contains": "urgent",
        "date_from": "2024-01-01",
        "date_to": "2024-12-31",
        "category": "business",
        "has_attachments": True,
        "limit": 50,
        "offset": 100,
    }

    result = await database_interface.search_emails(complex_filters)
    assert result == []


@pytest.mark.asyncio
async def test_search_emails_api_error_comprehensive(database_interface):
    """Test search_emails with API error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock API error - make sure the full mock chain raises the error
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.offset.return_value = mock_table
    mock_table.execute.side_effect = APIError(
        {"message": "Search API error", "details": "Query failed"}
    )
    mock_client.table.return_value = mock_table

    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.search_emails({"urgency": "high"})


# =============================================================================
# COMPREHENSIVE STATISTICS TESTS - Testing uncovered stats paths
# =============================================================================


@pytest.mark.asyncio
async def test_get_stats_not_connected_comprehensive(database_interface):
    """Test get_stats when not connected."""
    database_interface._connected = False

    with pytest.raises(RuntimeError, match="Database not connected"):
        await database_interface.get_stats()


@pytest.mark.asyncio
async def test_get_stats_rpc_error_comprehensive(database_interface):
    """Test get_stats with RPC call error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock RPC error
    mock_client.rpc.return_value.execute.side_effect = APIError(
        {"message": "RPC failed", "details": "Function error"}
    )

    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.get_stats()


@pytest.mark.asyncio
async def test_get_stats_with_data_aggregation_comprehensive(database_interface):
    """Test get_stats with successful data aggregation."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock successful RPC calls with stats data
    mock_basic_stats = MagicMock()
    mock_basic_stats.data = {
        "total_emails": 100,
        "total_analyzed": 95,
        "avg_urgency": 65.5,
    }

    mock_urgency_dist = MagicMock()
    mock_urgency_dist.data = [
        {"urgency_level": "low", "count": 30},
        {"urgency_level": "medium", "count": 40},
        {"urgency_level": "high", "count": 25},
        {"urgency_level": "critical", "count": 5},
    ]

    # Setup RPC mock responses
    def rpc_side_effect(func_name):
        if func_name == "get_email_stats":
            return mock_basic_stats
        elif func_name == "get_urgency_distribution":
            return mock_urgency_dist
        else:
            mock_resp = MagicMock()
            mock_resp.data = []
            return mock_resp

    mock_client.rpc.side_effect = rpc_side_effect
    mock_basic_stats.execute.return_value = mock_basic_stats
    mock_urgency_dist.execute.return_value = mock_urgency_dist

    result = await database_interface.get_stats()

    assert isinstance(result, EmailStats)
    mock_client.rpc.assert_called()


# =============================================================================
# COMPREHENSIVE SUBSCRIPTION TESTS - Testing uncovered subscription paths
# =============================================================================


@pytest.mark.asyncio
async def test_subscribe_to_changes_not_connected_comprehensive(database_interface):
    """Test real-time subscription when not connected."""
    database_interface._connected = False

    def dummy_callback(payload):
        pass

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        database_interface.subscribe_to_changes(dummy_callback)


@pytest.mark.asyncio
async def test_subscribe_to_changes_subscription_error_comprehensive(
    database_interface,
):
    """Test real-time subscription with subscription error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Mock subscription error
    mock_client.table.return_value.on.side_effect = Exception("Subscription failed")

    def dummy_callback(payload):
        pass

    with pytest.raises(Exception, match="Failed to create subscription"):
        database_interface.subscribe_to_changes(dummy_callback, {"urgency": "high"})


@pytest.mark.asyncio
async def test_unsubscribe_from_changes_nonexistent_comprehensive(database_interface):
    """Test unsubscribing from non-existent subscription."""
    database_interface._connected = True

    # Try to unsubscribe from non-existent subscription
    result = database_interface.unsubscribe_from_changes("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_unsubscribe_from_changes_error_comprehensive(database_interface):
    """Test unsubscribe with error during cleanup."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Add mock subscription
    mock_subscription = MagicMock()
    mock_subscription.unsubscribe.side_effect = Exception("Unsubscribe failed")
    database_interface._real_time_subscriptions["test-sub"] = mock_subscription

    # Should handle error gracefully (based on implementation)
    try:
        database_interface.unsubscribe_from_changes("test-sub")
    except Exception:
        pass  # Expected behavior


# =============================================================================
# COMPREHENSIVE DATA CONVERSION TESTS - Testing uncovered conversion paths
# =============================================================================


def test_processed_email_to_supabase_with_all_fields_comprehensive(
    database_interface, sample_processed_email
):
    """Test converting ProcessedEmail to Supabase format with all fields."""
    # Test conversion without adding invalid fields
    result = database_interface._processed_email_to_supabase(sample_processed_email)

    assert isinstance(result, dict)
    assert result["message_id"] == sample_processed_email.email_data.message_id
    assert result["subject"] == sample_processed_email.email_data.subject
    assert result["from_email"] == sample_processed_email.email_data.from_email
    assert result["to_emails"] == sample_processed_email.email_data.to_emails
    assert "status" in result
    assert "received_at" in result


def test_supabase_to_processed_email_with_missing_analysis_comprehensive(
    database_interface,
):
    """Test converting from Supabase format with missing analysis data."""
    supabase_data = {
        "id": "test-id",
        "message_id": "msg-123",
        "subject": "Test Subject",
        "from_email": "sender@example.com",
        "to_emails": ["recipient@example.com"],
        "text_body": "Test body",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": {},
        "attachments": [],
        "email_attachments": [],
        "email_analysis": [],
        # No analysis data
        "user_id": "test-user",
        "status": "received",
        "processed_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = database_interface._supabase_to_processed_email(supabase_data)

    assert result.id == "test-id"
    assert result.analysis is None


def test_supabase_to_processed_email_with_invalid_enum_comprehensive(
    database_interface,
):
    """Test converting from Supabase format with invalid enum values."""
    supabase_data = {
        "id": "test-id",
        "message_id": "msg-123",
        "subject": "Test Subject",
        "from_email": "sender@example.com",
        "to_emails": ["recipient@example.com"],
        "text_body": "Test body",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": {},
        "attachments": [],
        "email_attachments": [],
        "email_analysis": [],
        "urgency_level": "invalid_level",  # Invalid enum value
        "status": "analyzed",  # Valid status
        "processed_at": None,
        "user_id": "test-user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = database_interface._supabase_to_processed_email(supabase_data)

    # Should handle invalid enums gracefully
    assert result.id == "test-id"


# =============================================================================
# COMPREHENSIVE UTILITY METHOD TESTS - Testing uncovered utility paths
# =============================================================================


@pytest.mark.asyncio
async def test_disconnect_with_active_subscriptions_comprehensive(database_interface):
    """Test disconnect with active real-time subscriptions."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Add mock subscriptions
    mock_sub1 = MagicMock()
    mock_sub2 = MagicMock()
    database_interface._real_time_subscriptions = {"sub1": mock_sub1, "sub2": mock_sub2}

    await database_interface.disconnect()

    # Should disconnect but not clean subscriptions automatically
    assert database_interface._connected is False
    assert database_interface.client is None
    # Subscriptions remain (disconnect doesn't clean them)
    assert len(database_interface._real_time_subscriptions) == 2


def test_set_current_user_id_comprehensive(database_interface):
    """Test setting current user ID."""
    database_interface.set_current_user_id("new-user-123")
    assert database_interface.current_user_id == "new-user-123"


def test_get_current_user_id_comprehensive(database_interface):
    """Test getting current user ID."""
    database_interface.current_user_id = "test-user-456"
    assert database_interface.get_current_user_id() == "test-user-456"


def test_get_current_user_id_none_comprehensive(database_interface):
    """Test getting current user ID when None."""
    database_interface.current_user_id = None
    assert database_interface.get_current_user_id() is None


# =============================================================================
# COMPREHENSIVE ERROR HANDLING AND EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_multiple_operations_after_disconnect_comprehensive(database_interface):
    """Test multiple operations after disconnect."""
    # Ensure disconnected state
    database_interface._connected = False
    database_interface.client = None

    # All operations should raise not connected error
    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.store_email(MagicMock())

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.get_email("test-id")

    with pytest.raises(Exception, match=DB_NOT_CONNECTED_ERROR):
        await database_interface.search_emails({})


@pytest.mark.asyncio
async def test_config_initialization_edge_cases_comprehensive():
    """Test config initialization edge cases."""
    # Test with None config
    with patch(
        "src.supabase_integration.database_interface.SupabaseConfig"
    ) as mock_config_class:
        mock_config_class.return_value = MagicMock()
        db_interface = SupabaseDatabaseInterface(None)
        assert db_interface.config is not None


# =============================================================================
# COVERAGE IMPROVEMENT TESTS - Additional error handling and edge cases
# =============================================================================


@pytest.mark.asyncio
async def test_connect_test_query_exception_handling_coverage(
    database_interface, mock_supabase_config
):
    """Test connection test query exception handling (lines 71-74)."""
    with patch(
        "src.supabase_integration.database_interface.create_client"
    ) as mock_create_client:
        # Arrange
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.side_effect = Exception("Test query failed")
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client

        # Act
        await database_interface.connect()

        # Assert - should still connect even if test query fails
        assert database_interface._connected is True
        assert database_interface.client is mock_client


@pytest.mark.asyncio
async def test_store_email_api_error_coverage(
    database_interface, sample_processed_email
):
    """Test store_email API error handling (line 160)."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.side_effect = APIError({"message": "API Error occurred"})
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act & Assert
    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_store_email_general_exception_coverage(
    database_interface, sample_processed_email
):
    """Test store_email general exception handling (line 166)."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.side_effect = Exception("Unexpected error")
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to store email"):
        await database_interface.store_email(sample_processed_email)


@pytest.mark.asyncio
async def test_get_email_api_error_row_not_found_coverage(database_interface):
    """Test get_email API error with PGRST116 (row not found) (lines 196-213)."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = APIError({"message": "PGRST116: Row not found"})
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act
    result = await database_interface.get_email("nonexistent-id")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_email_api_error_other_coverage(database_interface):
    """Test get_email API error with other error codes."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = APIError({"message": "Other API error"})
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act & Assert
    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.get_email("test-id")


@pytest.mark.asyncio
async def test_get_email_general_exception_coverage(database_interface):
    """Test get_email general exception handling."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("Unexpected error")
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to retrieve email"):
        await database_interface.get_email("test-id")


@pytest.mark.asyncio
async def test_get_email_no_data_found_coverage(database_interface):
    """Test get_email when no data is found."""
    # Arrange
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_response = MagicMock()
    mock_response.data = []  # No data found
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Act
    result = await database_interface.get_email("nonexistent-id")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_search_emails_individual_filters(database_interface):
    """Test search_emails with individual filter conditions for better coverage."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock response
    mock_response = MagicMock()
    mock_response.data = []

    # Create a mock chain that supports all the query building methods
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_response

    mock_client.table.return_value = mock_query

    # Test sender filter (line 196)
    await database_interface.search_emails({"sender": "test@example.com"})
    mock_query.ilike.assert_called()

    # Test subject filter (line 199)
    await database_interface.search_emails({"subject": "test subject"})
    mock_query.ilike.assert_called()

    # Test status filter (line 202)
    await database_interface.search_emails({"status": "processed"})
    mock_query.eq.assert_called()

    # Test priority filter (line 205)
    await database_interface.search_emails({"priority": "high"})
    mock_query.eq.assert_called()

    # Test date_from filter (line 208)
    await database_interface.search_emails({"date_from": "2024-01-01"})
    mock_query.gte.assert_called()

    # Test date_to filter (line 211)
    await database_interface.search_emails({"date_to": "2024-12-31"})
    mock_query.lte.assert_called()


@pytest.mark.asyncio
async def test_search_emails_sorting_and_pagination(database_interface):
    """Test search_emails sorting and pagination parameters for coverage."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock response
    mock_response = MagicMock()
    mock_response.data = []

    # Create a mock chain
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_response

    mock_client.table.return_value = mock_query

    # Test custom sorting and pagination parameters
    query_params = {
        "order_by": "created_at",
        "order_desc": False,
        "limit": 50,
        "offset": 20,
    }

    await database_interface.search_emails(query_params)

    # Verify the methods were called with correct parameters
    mock_query.order.assert_called_with("created_at", desc=False)
    mock_query.limit.assert_called_with(50)
    mock_query.offset.assert_called_with(20)


@pytest.mark.asyncio
async def test_search_emails_data_conversion(database_interface):
    """Test search_emails data conversion logic for coverage."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock response with sample data
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "email-1",
            "subject": "Test Email",
            "sender": "test@example.com",
            "received_date": "2024-01-01T00:00:00Z",
            "email_analysis": [{"urgency_score": 75}],
            "email_attachments": [],
        }
    ]

    # Create a mock chain
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    # Add ilike for sender filter
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.execute.return_value = mock_response

    mock_client.table.return_value = mock_query

    # Mock the conversion method to return a ProcessedEmail
    with patch.object(
        database_interface, "_supabase_to_processed_email"
    ) as mock_convert:
        mock_processed_email = MagicMock()
        mock_convert.return_value = mock_processed_email

        result = await database_interface.search_emails({"sender": "test@example.com"})

        # Verify conversion was called and result contains the converted email
        mock_convert.assert_called_once()
        assert result == [mock_processed_email]


@pytest.mark.asyncio
async def test_get_stats_method_coverage(database_interface):
    """Test get_stats method for better coverage of missing lines."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Mock responses for different RPC calls
    total_response = MagicMock()
    total_response.count = 100

    # Create proper mock responses that return actual data
    status_response = MagicMock()
    status_response.data = [
        {"status": "high", "count": 25},
        {"status": "medium", "count": 50},
        {"status": "low", "count": 25},
    ]

    priority_response = MagicMock()
    priority_response.data = [{"priority": "urgent", "count": 15}]

    metrics_response = MagicMock()
    metrics_response.data = [
        {"avg_urgency_score": 65.5, "avg_processing_time": 2.5, "success_rate": 95.0}
    ]

    # Setup mock table and RPC calls
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.execute.return_value = total_response

    mock_client.table.return_value = mock_table

    # Create mock execute methods that return the proper response objects
    status_mock = MagicMock()
    status_mock.execute.return_value = status_response

    priority_mock = MagicMock()
    priority_mock.execute.return_value = priority_response

    metrics_mock = MagicMock()
    metrics_mock.execute.return_value = metrics_response

    # Make sure the RPC calls return the correct mocks in the right order
    def rpc_side_effect(name, *args, **kwargs):
        if name == "get_email_stats_by_status":
            return status_mock
        elif name == "get_email_stats_by_priority":
            return priority_mock
        elif name == "get_email_processing_metrics":
            return metrics_mock
        return MagicMock()

    mock_client.rpc.side_effect = rpc_side_effect
    result = await database_interface.get_stats()

    # Debug: Print what we actually got
    print(f"Result urgency_distribution: {result.urgency_distribution}")
    print(f"Result total_processed: {result.total_processed}")

    assert isinstance(result, EmailStats)
    assert result.total_processed == 100
    assert result.urgency_distribution.get(UrgencyLevel.HIGH, 0) == 25
    # Check that urgent priority emails are properly counted in urgency_distribution
    assert result.avg_urgency_score == 65.5


@pytest.mark.asyncio
async def test_get_stats_with_empty_data(database_interface):
    """Test get_stats method with empty data responses for edge case coverage."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Mock empty responses
    total_response = MagicMock()
    total_response.count = None  # Test None count handling

    status_response = MagicMock()
    status_response.data = []

    priority_response = MagicMock()
    priority_response.data = []

    metrics_response = MagicMock()
    metrics_response.data = []

    # Setup mock calls
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.execute.return_value = total_response

    mock_client.table.return_value = mock_table

    # Create mock execute methods that return the proper response objects
    status_mock = MagicMock()
    status_mock.execute.return_value = status_response

    priority_mock = MagicMock()
    priority_mock.execute.return_value = priority_response

    metrics_mock = MagicMock()
    metrics_mock.execute.return_value = metrics_response

    mock_client.rpc.side_effect = [status_mock, priority_mock, metrics_mock]

    # Call get_stats with empty data
    result = await database_interface.get_stats()

    assert isinstance(result, EmailStats)
    assert result.total_processed == 0  # Should default to 0 when count is None
    assert result.urgency_distribution.get(UrgencyLevel.HIGH, 0) == 0


@pytest.mark.asyncio
async def test_get_stats_api_error(database_interface):
    """Test get_stats method with API error for error handling coverage."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Mock API error on first RPC call
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.execute.side_effect = APIError({"message": "RPC error"})

    mock_client.table.return_value = mock_table

    # Verify API error is properly handled
    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.get_stats()


# =============================================================================
# AUTHENTICATION METHODS COVERAGE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_authenticate_user_success(database_interface):
    """Test successful user authentication."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock successful authentication response
    mock_user = MagicMock()
    mock_user.id = "auth-user-123"
    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_client.auth.sign_in_with_password.return_value = mock_response

    # Test authentication
    result = await database_interface.authenticate_user(
        "user@example.com", "password123"
    )

    assert result is True
    assert database_interface.current_user_id == "auth-user-123"
    mock_client.auth.sign_in_with_password.assert_called_once_with(
        {"email": "user@example.com", "password": "password123"}
    )


@pytest.mark.asyncio
async def test_authenticate_user_failure(database_interface):
    """Test failed user authentication."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock failed authentication response
    mock_response = MagicMock()
    mock_response.user = None

    mock_client.auth.sign_in_with_password.return_value = mock_response

    # Test authentication failure
    result = await database_interface.authenticate_user(
        "user@example.com", "wrongpassword"
    )

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_user_not_connected(database_interface):
    """Test authentication when not connected."""
    database_interface.client = None

    with pytest.raises(RuntimeError, match="Database not connected"):
        await database_interface.authenticate_user("user@example.com", "password123")


@pytest.mark.asyncio
async def test_authenticate_user_exception(database_interface):
    """Test authentication with exception."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock exception
    mock_client.auth.sign_in_with_password.side_effect = Exception("Auth service error")

    with pytest.raises(ValueError, match="Authentication failed"):
        await database_interface.authenticate_user("user@example.com", "password123")


@pytest.mark.asyncio
async def test_register_user_success(database_interface):
    """Test successful user registration."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock successful registration response
    mock_user = MagicMock()
    mock_user.id = "new-user-456"
    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_client.auth.sign_up.return_value = mock_response

    # Test registration
    metadata = {"name": "Test User", "role": "user"}
    result = await database_interface.register_user(
        "newuser@example.com", "password123", metadata
    )

    assert result == "new-user-456"
    mock_client.auth.sign_up.assert_called_once_with(
        {
            "email": "newuser@example.com",
            "password": "password123",
            "options": {"data": metadata},
        }
    )


@pytest.mark.asyncio
async def test_register_user_failure(database_interface):
    """Test failed user registration."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock failed registration response
    mock_response = MagicMock()
    mock_response.user = None

    mock_client.auth.sign_up.return_value = mock_response

    with pytest.raises(ValueError, match="User registration failed"):
        await database_interface.register_user("newuser@example.com", "password123")


@pytest.mark.asyncio
async def test_register_user_not_connected(database_interface):
    """Test registration when not connected."""
    database_interface.client = None

    with pytest.raises(RuntimeError, match="Database not connected"):
        await database_interface.register_user("newuser@example.com", "password123")


@pytest.mark.asyncio
async def test_register_user_exception(database_interface):
    """Test registration with exception."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock exception
    mock_client.auth.sign_up.side_effect = Exception("Registration service error")

    with pytest.raises(ValueError, match="Registration failed"):
        await database_interface.register_user("newuser@example.com", "password123")


@pytest.mark.asyncio
async def test_register_user_with_no_metadata(database_interface):
    """Test registration without metadata."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock successful registration response
    mock_user = MagicMock()
    mock_user.id = "new-user-789"
    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_client.auth.sign_up.return_value = mock_response

    # Test registration without metadata
    result = await database_interface.register_user(
        "newuser@example.com", "password123"
    )

    assert result == "new-user-789"
    mock_client.auth.sign_up.assert_called_once_with(
        {
            "email": "newuser@example.com",
            "password": "password123",
            "options": {"data": {}},  # Should default to empty dict
        }
    )


# =============================================================================
# REAL-TIME SUBSCRIPTION COVERAGE TESTS
# =============================================================================


def test_subscribe_to_email_changes_basic(database_interface):
    """Test basic email subscription functionality."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock channel
    mock_channel = MagicMock()
    mock_client.channel.return_value = mock_channel

    # Test subscription
    callback = MagicMock()
    result = database_interface.subscribe_to_email_changes(callback)

    assert result == mock_channel
    mock_client.channel.assert_called_once_with("email_changes")
    mock_channel.on.assert_called_once()
    mock_channel.subscribe.assert_called_once()


def test_subscribe_to_email_changes_with_filters(database_interface):
    """Test email subscription with filters."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client

    # Mock channel
    mock_channel = MagicMock()
    mock_client.channel.return_value = mock_channel

    # Test subscription with user filter
    callback = MagicMock()
    filters = {"user_id": "test-user-123"}
    result = database_interface.subscribe_to_email_changes(callback, filters)

    assert result == mock_channel
    mock_channel.on.assert_called_once()
    # Verify the filter configuration is applied
    call_args = mock_channel.on.call_args[0]
    assert call_args[0] == "postgres_changes"


def test_subscribe_to_email_changes_not_connected(database_interface):
    """Test subscription when not connected."""
    database_interface.client = None

    with pytest.raises(RuntimeError, match="Database not connected"):
        database_interface.subscribe_to_email_changes(MagicMock())


# =============================================================================
# USER CONTEXT METHODS COVERAGE TESTS
# =============================================================================


def test_get_current_user_id(database_interface):
    """Test getting current user ID."""
    # Set a user ID
    database_interface.current_user_id = "current-user-123"

    result = database_interface.get_current_user_id()
    assert result == "current-user-123"


def test_get_current_user_id_none(database_interface):
    """Test getting current user ID when none set."""
    database_interface.current_user_id = None

    result = database_interface.get_current_user_id()
    assert result is None


@pytest.mark.asyncio
async def test_set_user_context(database_interface):
    """Test setting user context."""
    await database_interface.set_user_context("context-user-789")

    assert database_interface.current_user_id == "context-user-789"


# =============================================================================
# ADDITIONAL ERROR HANDLING COVERAGE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_search_emails_runtime_error(database_interface):
    """Test search_emails with non-API runtime error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock non-API exception
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.offset.return_value = mock_table
    mock_table.execute.side_effect = Exception("Database connection lost")

    mock_client.table.return_value = mock_table

    with pytest.raises(RuntimeError, match="Failed to search emails"):
        await database_interface.search_emails({"urgency": "high"})


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_stats_runtime_error(database_interface):
    """Test get_stats with non-API runtime error."""
    # Setup mock client
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Mock non-API exception on table count query
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.execute.side_effect = Exception("Database connection lost")

    mock_client.table.return_value = mock_table

    # Should raise RuntimeError for general database errors
    with pytest.raises(RuntimeError, match="Failed to get stats"):
        await database_interface.get_stats()


# =============================================================================
# ADDITIONAL CONVERSION METHOD COVERAGE TESTS
# =============================================================================


def test_supabase_to_processed_email_minimal_data(database_interface):
    """Test conversion with minimal required data."""
    minimal_data = {
        "id": "minimal-email",
        "subject": "Minimal Subject",
        "from_email": "minimal@example.com",
        "to_emails": ["recipient@example.com"],
        "text_body": "Minimal body",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": {},
        "attachments": [],
        "email_attachments": [],
        "email_analysis": [],
        "status": "received",  # Use valid EmailStatus enum value
        "processed_at": None,
        "user_id": "test-user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_id": "minimal-message-id@example.com",  # Add required message_id
    }

    result = database_interface._supabase_to_processed_email(minimal_data)
    assert result.id == "minimal-email"
    assert result.email_data.subject == "Minimal Subject"


# =============================================================================
# COMPREHENSIVE ERROR HANDLING AND EDGE CASES TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_store_email_api_error_handling(database_interface):
    """Test store_email with various API error scenarios."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Create sample email
    email_data = EmailData(
        message_id="error-test@example.com",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        subject="Error Test",
        text_body="Testing error handling",
        received_at=datetime.now(timezone.utc),
        headers={},
        attachments=[],
    )
    email = ProcessedEmail(
        id="error-email-123",
        email_data=email_data,
        status=EmailStatus.RECEIVED,
        processed_at=None,
        analysis=None,
    )

    # Test API error during email insert
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.side_effect = APIError(
        {"code": "403", "message": "Permission denied - RLS violation"}
    )
    mock_client.table.return_value = mock_table

    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.store_email(email)


@pytest.mark.asyncio
async def test_store_email_with_attachments_error(database_interface):
    """Test store_email error handling during attachment storage."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Create email with attachments
    attachment = AttachmentData(
        name="test.pdf",
        content_type="application/pdf",
        size=1024,
        content_id="att-123",
    )
    email_data = EmailData(
        message_id="attachment-error@example.com",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        subject="Attachment Test",
        text_body="Testing attachment storage error",
        received_at=datetime.now(timezone.utc),
        headers={},
        attachments=[attachment],
    )
    email = ProcessedEmail(
        id="attach-email-123",
        email_data=email_data,
        status=EmailStatus.RECEIVED,
        processed_at=None,
        analysis=None,
    )

    # Mock successful email insert but failed attachment insert
    mock_email_table = MagicMock()
    mock_email_table.upsert.return_value = mock_email_table
    mock_email_table.execute.return_value.data = [{"id": "email-123"}]

    mock_attachment_table = MagicMock()
    mock_attachment_table.insert.return_value = mock_attachment_table
    mock_attachment_table.execute.side_effect = Exception("Attachment storage failed")

    def table_side_effect(table_name):
        if table_name == "emails":
            return mock_email_table
        elif table_name == "email_attachments":
            return mock_attachment_table
        return MagicMock()

    mock_client.table.side_effect = table_side_effect

    with pytest.raises(RuntimeError, match="Failed to store email"):
        await database_interface.store_email(email)


@pytest.mark.asyncio
async def test_store_email_empty_response_error(database_interface):
    """Test store_email when no data is returned from database."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True

    # Create sample email
    email_data = EmailData(
        message_id="empty-response@example.com",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"],
        subject="Empty Response Test",
        text_body="Testing empty response handling",
        received_at=datetime.now(timezone.utc),
        headers={},
        attachments=[],
    )
    email = ProcessedEmail(
        id="empty-email-123",
        email_data=email_data,
        status=EmailStatus.RECEIVED,
        processed_at=None,
        analysis=None,
    )

    # Mock empty response
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value.data = []  # Empty response
    mock_client.table.return_value = mock_table

    with pytest.raises(
        RuntimeError,
        match="Failed to store email: Failed to store email - no data returned",
    ):
        await database_interface.store_email(email)


# =============================================================================
# DATA CONVERSION METHOD TESTS
# =============================================================================


def test_has_ai_analysis_true_conditions(database_interface):
    """Test _has_ai_analysis method for conditions that should return True."""
    # Test with SambaNova tags
    analysis = EmailAnalysis(
        urgency_score=5,
        urgency_level=UrgencyLevel.MEDIUM,
        sentiment="positive",
        confidence=0.75,
        keywords=["meeting", "urgent"],
        action_items=["Review document"],
        temporal_references=["tomorrow"],
        tags=["sambanova_processed", "high_priority"],
        category="business",
    )
    assert database_interface._has_ai_analysis(analysis) is True

    # Test with AI-prefixed tags
    analysis_ai = EmailAnalysis(
        urgency_score=3,
        urgency_level=UrgencyLevel.LOW,
        sentiment="neutral",
        confidence=0.60,
        keywords=[],
        action_items=[],
        temporal_references=[],
        tags=["ai_enhanced", "automated"],
        category="general",
    )
    assert database_interface._has_ai_analysis(analysis_ai) is True

    # Test with high confidence
    analysis_high_conf = EmailAnalysis(
        urgency_score=7,
        urgency_level=UrgencyLevel.HIGH,
        sentiment="negative",
        confidence=0.95,  # High confidence
        keywords=["deadline"],
        action_items=[],
        temporal_references=[],
        tags=["priority"],
        category="urgent",
    )
    assert database_interface._has_ai_analysis(analysis_high_conf) is True


def test_has_ai_analysis_false_conditions(database_interface):
    """Test _has_ai_analysis method for conditions that should return False."""
    analysis = EmailAnalysis(
        urgency_score=2,
        urgency_level=UrgencyLevel.LOW,
        sentiment="neutral",
        confidence=0.70,  # Below threshold
        keywords=["general"],
        action_items=[],
        temporal_references=[],
        tags=["standard", "email"],  # No AI-related tags
        category="general",
    )
    assert database_interface._has_ai_analysis(analysis) is False


def test_extract_ai_analysis_comprehensive(database_interface):
    """Test _extract_ai_analysis method with comprehensive analysis data."""
    analysis = EmailAnalysis(
        urgency_score=8,
        urgency_level=UrgencyLevel.HIGH,
        sentiment="urgent",
        confidence=0.92,
        keywords=["deadline", "critical", "asap"],
        action_items=["Submit report", "Schedule meeting", "Review contract"],
        temporal_references=["today", "this afternoon"],
        tags=["sambanova_enhanced", "priority"],
        category="business_critical",
    )

    result = database_interface._extract_ai_analysis(analysis)

    # Verify structure
    assert "sambanova_version" in result
    assert "processing_timestamp" in result
    assert "confidence" in result
    assert result["confidence"] == 0.92

    # Verify task extraction
    assert "task_extraction" in result
    task_data = result["task_extraction"]
    assert "tasks" in task_data
    assert "overall_urgency" in task_data
    assert "extraction_confidence" in task_data
    assert len(task_data["tasks"]) == 3
    assert task_data["overall_urgency"] == 8
    assert task_data["extraction_confidence"] == 0.92

    # Verify each task
    for i, expected_task in enumerate(
        ["Submit report", "Schedule meeting", "Review contract"]
    ):
        task = task_data["tasks"][i]
        assert task["description"] == expected_task
        assert task["extraction_method"] == "sambanova"
        assert task["confidence"] == 0.92

    # Verify sentiment analysis
    assert "sentiment_analysis" in result
    sentiment_data = result["sentiment_analysis"]
    assert sentiment_data["sentiment"] == "urgent"
    assert sentiment_data["confidence"] == 0.92
    assert sentiment_data["urgency_level"] == "high"

    # Verify context analysis
    assert "context_analysis" in result
    context_data = result["context_analysis"]
    assert context_data["context_keywords"] == ["deadline", "critical", "asap"]
    assert context_data["business_context"] == "business_critical"


def test_extract_ai_analysis_minimal_data(database_interface):
    """Test _extract_ai_analysis with minimal analysis data."""
    analysis = EmailAnalysis(
        urgency_score=3,
        urgency_level=UrgencyLevel.LOW,
        sentiment="neutral",
        confidence=0.65,
        keywords=[],
        action_items=[],
        temporal_references=[],
        tags=[],
        category=None,
    )

    result = database_interface._extract_ai_analysis(analysis)

    # Basic structure should exist
    assert "sambanova_version" in result
    assert "processing_timestamp" in result
    assert "confidence" in result
    assert result["confidence"] == 0.65

    # Sentiment analysis should always be present
    assert "sentiment_analysis" in result
    sentiment_data = result["sentiment_analysis"]
    assert sentiment_data["sentiment"] == "neutral"
    assert sentiment_data["confidence"] == 0.65
    assert sentiment_data["urgency_level"] == "low"

    # Task extraction and context analysis should not be present for empty data
    assert "task_extraction" not in result
    assert "context_analysis" not in result


# =============================================================================
# REAL-TIME SUBSCRIPTION HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_urgent_emails_realtime_success(database_interface):
    """Test get_urgent_emails_realtime method success case."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock successful response with urgent emails
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "urgent-1",
            "subject": "URGENT: System Down",
            "urgency_score": 9,
            "from_email": "admin@company.com",
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "urgent-2",
            "subject": "Critical Security Alert",
            "urgency_score": 8,
            "from_email": "security@company.com",
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = mock_response

    mock_client.table.return_value = mock_table

    result = await database_interface.get_urgent_emails_realtime()

    assert len(result) == 2
    assert result[0]["id"] == "urgent-1"
    assert result[1]["id"] == "urgent-2"
    # Verify the query was constructed correctly
    mock_table.gte.assert_called_with("urgency_score", 70)
    # Note: The current implementation doesn't filter by user_id in get_urgent_emails_realtime


@pytest.mark.asyncio
async def test_get_urgent_emails_realtime_no_user_context(database_interface):
    """Test get_urgent_emails_realtime without user context."""
    database_interface.client = MagicMock()
    database_interface._connected = True
    database_interface.current_user_id = None

    # The current implementation doesn't check user context, so it should work
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])

    database_interface.client.table.return_value = mock_table

    result = await database_interface.get_urgent_emails_realtime()
    assert result == []


@pytest.mark.asyncio
async def test_get_ai_enhanced_emails_success(database_interface):
    """Test get_ai_enhanced_emails method success case."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock successful response with AI-enhanced emails
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "ai-email-1",
            "subject": "AI Enhanced Email",
            "from_email": "ai@company.com",
            "ai_analysis_result": {"confidence": 0.95, "enhancement": "sambanova"},
            "ai_processed_at": "2023-01-01T12:00:00Z",
            "urgency_score": 85,
        }
    ]

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = mock_response

    # Set up the not_.is_ chain properly
    mock_not = MagicMock()
    mock_not.is_ = MagicMock(return_value=mock_table)
    mock_table.not_ = mock_not

    mock_client.table.return_value = mock_table

    result = await database_interface.get_ai_enhanced_emails(limit=10)

    assert len(result) == 1
    assert result[0]["id"] == "ai-email-1"
    # Verify the query was constructed correctly
    mock_table.select.assert_called_with(
        "id, subject, from_email, ai_analysis_result, ai_processed_at, urgency_score"
    )
    mock_table.not_.is_.assert_called_with("ai_analysis_result", "null")
    mock_table.eq.assert_called_with("ai_processing_enabled", True)
    mock_table.order.assert_called_with("ai_processed_at", desc=True)
    mock_table.limit.assert_called_with(10)


@pytest.mark.asyncio
async def test_get_ai_enhanced_emails_api_error(database_interface):
    """Test get_ai_enhanced_emails with API error."""
    mock_client = MagicMock()
    database_interface.client = mock_client
    database_interface._connected = True
    database_interface.current_user_id = "test-user-123"

    # Mock API error - set up the proper chain
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table

    # Set up the not_.is_ chain properly
    mock_not = MagicMock()
    mock_not.is_ = MagicMock(return_value=mock_table)
    mock_table.not_ = mock_not

    mock_table.execute.side_effect = APIError(
        {"code": "TIMEOUT", "message": "Database timeout"}
    )

    mock_client.table.return_value = mock_table

    with pytest.raises(ValueError, match="Supabase API error"):
        await database_interface.get_ai_enhanced_emails()


# =============================================================================
# EDGE CASES FOR ATTACHMENTS
# =============================================================================


def test_attachments_to_supabase_various_sizes(database_interface):
    """Test _attachments_to_supabase with various attachment sizes and types."""

    # Create objects that mimic the AttachmentData structure
    class MockAttachment:
        def __init__(self, filename, content_type, size=None, content=None):
            self.filename = filename
            self.content_type = content_type
            self.size = size if size is not None else 0
            self.content = content

    attachments = [
        MockAttachment("small.txt", "text/plain", 100, "small file content"),
        MockAttachment("large_video.mp4", "video/mp4", 104857600, "binary video data"),
        MockAttachment(
            "no_size.doc", "application/msword"
        ),  # Missing size - should default to 0
        MockAttachment("special-chars-ñáé.pdf", "application/pdf", 2048, "pdf content"),
    ]

    result = database_interface._attachments_to_supabase(attachments, "email-123")

    assert len(result) == 4

    # Check small file
    assert result[0]["filename"] == "small.txt"
    assert result[0]["size"] == 100

    # Check large file
    assert result[1]["filename"] == "large_video.mp4"
    assert result[1]["size"] == 104857600

    # Check missing size defaults to 0
    assert result[2]["filename"] == "no_size.doc"
    assert result[2]["size"] == 0

    # Check special characters
    assert result[3]["filename"] == "special-chars-ñáé.pdf"
    assert result[3]["size"] == 2048

    # All should have email_id and created_at
    for attachment in result:
        assert attachment["email_id"] == "email-123"
        assert "created_at" in attachment


def test_attachments_to_supabase_empty_list(database_interface):
    """Test _attachments_to_supabase with empty attachment list."""
    result = database_interface._attachments_to_supabase([], "email-123")
    assert result == []


def test_attachments_to_supabase_with_storage_path(database_interface):
    """Test _attachments_to_supabase with storage_path attribute."""

    class AttachmentWithPath:
        def __init__(self, filename, content_type, size, storage_path):
            self.filename = filename
            self.content_type = content_type
            self.size = size
            self.storage_path = storage_path

    attachments = [
        AttachmentWithPath(
            "cloud_file.pdf", "application/pdf", 1024, "/cloud/storage/path/file.pdf"
        )
    ]

    result = database_interface._attachments_to_supabase(attachments, "email-123")

    assert len(result) == 1
    assert result[0]["filename"] == "cloud_file.pdf"
    assert result[0]["storage_path"] == "/cloud/storage/path/file.pdf"
