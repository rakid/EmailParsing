"""Unit tests for server.py - MCP Email Parsing Server"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Add src directory to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src import server, storage

# handle_call_tool est maintenant disponible via server.handle_call_tool
from src.config import config  # Import config for server metadata
from src.mcp.types import (
    PromptMessage,
    TextContent,
)
from src.models import (
    EmailAnalysis,
    EmailData,
    EmailStatus,
    ProcessedEmail,
    UrgencyLevel,
)

# Add src directory to path for imports (same as server.py)
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)


class TestServerInitialization:
    """Test MCP server initialization"""

    def test_server_instance_exists(self):
        """Test that server instance is created"""
        assert server.server is not None
        assert hasattr(server.server, "name")
        assert hasattr(server.server, "version")

    def test_server_metadata(self):
        """Test server metadata configuration"""
        assert server.server.name == config.server_name
        assert server.server.version == config.server_version
        assert "MCP server for unified email entry" in server.server.instructions


class TestResourceHandling:
    """Test MCP resource handling"""

    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        # Ensure server module uses the same storage instance
        server.storage = storage

    @pytest.mark.asyncio
    async def test_list_resources_basic(self):  # Renamed from test_list_resources
        """Test listing available base resources"""
        resources = await server.handle_list_resources()

        assert isinstance(resources, list)
        # Check for at least the 6 static resources
        assert len(resources) >= 6

        expected_static_uris = [
            "email://processed",
            "email://stats",
            "email://recent",
            "email://analytics",
            "email://high-urgency",
            "email://tasks",
        ]
        resource_uris = [str(r.uri) for r in resources]

        for uri in expected_static_uris:
            assert uri in resource_uris

    @pytest.mark.asyncio
    async def test_list_resources_with_dynamic_email_uris(self, sample_email_data):
        """Test that list_resources includes URIs for emails in storage."""
        # Add some emails to storage
        for i in range(3):
            email_data = EmailData(
                **{**sample_email_data, "message_id": f"dynamic-{i}"}
            )
            processed_email = ProcessedEmail(
                id=f"dynamic-id-{i}",
                email_data=email_data,
                status=EmailStatus.ANALYZED,
            )
            storage.email_storage[f"dynamic-id-{i}"] = processed_email

        resources = await server.handle_list_resources()
        resource_uris = [str(r.uri) for r in resources]

        # Check if URIs for the added emails are present
        assert "email://processed/dynamic-id-0" in resource_uris
        assert "email://processed/dynamic-id-1" in resource_uris
        assert "email://processed/dynamic-id-2" in resource_uris
        # Check that it doesn't list more than 10 dynamic URIs even if more are in storage
        for i in range(12):  # Add more emails
            email_data = EmailData(
                **{**sample_email_data, "message_id": f"limit-test-{i}"}
            )
            processed_email = ProcessedEmail(id=f"limit-id-{i}", email_data=email_data)
            storage.email_storage[f"limit-id-{i}"] = processed_email

        resources_limited = await server.handle_list_resources()
        dynamic_processed_uris = [
            r for r in resources_limited if str(r.uri).startswith("email://processed/")
        ]
        # 6 static + 10 dynamic = 16 if there are at least 10 emails.
        # If less than 10 emails, then 6 + number of emails
        num_dynamic_uris = min(len(storage.email_storage), 10)
        assert len(dynamic_processed_uris) == num_dynamic_uris

    @pytest.mark.asyncio
    async def test_read_processed_emails_resource(
        self, sample_email_data, sample_analysis_data
    ):
        """Test reading processed emails resource"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="test-email-1",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
        )
        storage.email_storage["test-email-1"] = processed_email

        result_str = await server.handle_read_resource("email://processed")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert "total_count" in data
        assert "emails" in data
        assert data["total_count"] == 1
        assert len(data["emails"]) == 1
        assert data["emails"][0]["id"] == "test-email-1"

    @pytest.mark.asyncio
    async def test_read_stats_resource(self):
        """Test reading email statistics resource"""
        storage.stats.total_processed = 5
        storage.stats.total_errors = 1
        storage.stats.avg_urgency_score = 65.5

        result_str = await server.handle_read_resource("email://stats")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert data["total_processed"] == 5
        assert data["total_errors"] == 1
        assert data["avg_urgency_score"] == pytest.approx(65.5)
        assert (
            data["resource_info"]["total_emails_in_storage"] == 0
        )  # No emails added to storage.email_storage

    @pytest.mark.asyncio
    async def test_read_recent_emails_resource(self, sample_email_data):
        """Test reading recent emails resource"""
        for i in range(15):
            email_data = EmailData(
                **{
                    **sample_email_data,
                    "message_id": f"recent-{i}",
                    "received_at": datetime.now(timezone.utc)
                    - timedelta(minutes=i),  # Ensure different times for sorting
                }
            )
            # Create a ProcessedEmail instance correctly
            processed_email = ProcessedEmail(
                id=f"recent-id-{i}",
                email_data=email_data,
                processed_at=datetime.now(timezone.utc)
                - timedelta(minutes=i),  # Add processed_at for sorting
            )
            storage.email_storage[f"recent-id-{i}"] = processed_email

        result_str = await server.handle_read_resource("email://recent")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert "count" in data
        assert "emails" in data
        assert data["count"] == 10
        assert len(data["emails"]) == 10
        # Ensure it returns the *most* recent
        assert data["emails"][0]["email_data"]["message_id"] == "recent-0"
        assert data["emails"][9]["email_data"]["message_id"] == "recent-9"

    @pytest.mark.asyncio
    async def test_read_analytics_resource_no_emails(self):
        """Test reading analytics resource when no emails are present."""
        result_str = await server.handle_read_resource("email://analytics")
        data = json.loads(result_str)
        assert data["message"] == "No emails processed yet"

    @pytest.mark.asyncio
    async def test_read_analytics_resource_no_analyzed_emails(self, sample_email_data):
        """Test reading analytics resource when emails exist but none are analyzed."""
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="test-no-analysis",
            email_data=email_data,
            analysis=None,  # No analysis
            status=EmailStatus.RECEIVED,
        )
        storage.email_storage["test-no-analysis"] = processed_email

        result_str = await server.handle_read_resource("email://analytics")
        data = json.loads(result_str)
        assert data["message"] == "No analyzed emails found"

    @pytest.mark.asyncio
    async def test_read_analytics_resource_with_data(
        self, sample_email_data, sample_analysis_data
    ):
        """Test reading analytics resource"""
        urgency_levels = [UrgencyLevel.LOW, UrgencyLevel.MEDIUM, UrgencyLevel.HIGH]
        for i, level in enumerate(urgency_levels):
            # Ensure sample_analysis_data is mutable for each iteration
            current_analysis_data = sample_analysis_data.copy()
            current_analysis_data["urgency_level"] = level
            current_analysis_data["urgency_score"] = 25 + (i * 25)  # 25, 50, 75
            analysis = EmailAnalysis(**current_analysis_data)

            email_data = EmailData(
                **{**sample_email_data, "message_id": f"analytics-{i}"}
            )
            processed_email = ProcessedEmail(
                id=f"analytics-{i}", email_data=email_data, analysis=analysis
            )
            storage.email_storage[f"analytics-{i}"] = processed_email

        result_str = await server.handle_read_resource("email://analytics")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert "total_emails" in data
        assert "urgency_distribution" in data
        assert "sentiment_distribution" in data
        assert data["total_emails"] == 3
        assert data["analyzed_emails"] == 3
        assert data["urgency_distribution"]["high"] == 1
        assert data["urgency_stats"]["average"] == pytest.approx(50.0)  # (25+50+75)/3

    @pytest.mark.asyncio
    async def test_read_high_urgency_resource(
        self, sample_email_data, sample_analysis_data
    ):
        """Test reading high urgency emails resource"""
        urgency_configs = [
            ("low-1", UrgencyLevel.LOW, 20),
            ("high-1", UrgencyLevel.HIGH, 80),  # This should be matched
            ("medium-1", UrgencyLevel.MEDIUM, 50),
            ("high-2", UrgencyLevel.HIGH, 90),  # This should be matched
        ]

        for email_id, urgency_level, urgency_score in urgency_configs:
            current_analysis_data = sample_analysis_data.copy()
            current_analysis_data["urgency_level"] = urgency_level
            current_analysis_data["urgency_score"] = urgency_score
            analysis = EmailAnalysis(**current_analysis_data)

            email_data = EmailData(**{**sample_email_data, "message_id": email_id})
            processed_email = ProcessedEmail(
                id=email_id, email_data=email_data, analysis=analysis
            )
            storage.email_storage[email_id] = processed_email

        result_str = await server.handle_read_resource("email://high-urgency")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert "count" in data
        assert "emails" in data
        assert data["count"] == 2
        assert len(data["emails"]) == 2
        email_ids_returned = {e["id"] for e in data["emails"]}
        assert "high-1" in email_ids_returned
        assert "high-2" in email_ids_returned

    @pytest.mark.asyncio
    async def test_read_tasks_resource(self, sample_email_data, sample_analysis_data):
        """Test reading tasks resource"""
        urgency_scores = [30, 50, 70]  # Only 50 and 70 should be included (>= 40)
        for i, score in enumerate(urgency_scores):
            current_analysis_data = sample_analysis_data.copy()
            current_analysis_data["urgency_score"] = score
            current_analysis_data["action_items"] = [f"Task for score {score}"]
            analysis = EmailAnalysis(**current_analysis_data)

            email_data = EmailData(**{**sample_email_data, "message_id": f"task-{i}"})
            processed_email = ProcessedEmail(
                id=f"task-{i}", email_data=email_data, analysis=analysis
            )
            storage.email_storage[f"task-{i}"] = processed_email

        result_str = await server.handle_read_resource("email://tasks")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert "total_tasks" in data
        assert "tasks" in data
        assert data["urgency_threshold"] == 40
        assert data["total_tasks"] == 2
        assert data["tasks"][0]["urgency_score"] == 70  # Sorted by urgency
        assert data["tasks"][1]["urgency_score"] == 50

    @pytest.mark.asyncio
    async def test_read_specific_email_resource(
        self, sample_email_data, sample_analysis_data
    ):
        """Test reading specific email resource"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="specific-email", email_data=email_data, analysis=analysis
        )
        storage.email_storage["specific-email"] = processed_email

        result_str = await server.handle_read_resource(
            "email://processed/specific-email"
        )

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert data["id"] == "specific-email"
        assert "resource_info" in data
        assert data["resource_info"]["email_id"] == "specific-email"

    @pytest.mark.asyncio
    async def test_read_resource_error_handling(self):
        """Test read_resource error handling for various scenarios"""
        # Test with non-existent resource URI
        with pytest.raises(
            ValueError, match="Unknown resource: email://nonexistent-uri"
        ):
            await server.handle_read_resource("email://nonexistent-uri")

        # Test with non-existent email ID
        with pytest.raises(ValueError, match="Email not found: nonexistent-id"):
            await server.handle_read_resource("email://processed/nonexistent-id")

        # Test with malformed URI (though Pydantic's AnyUrl might catch this earlier in a real scenario)
        # For this direct call, a simple string is passed, so ValueError from unknown resource is expected
        with pytest.raises(
            ValueError, match="Unknown resource: invalid-uri-scheme://test"
        ):
            await server.handle_read_resource("invalid-uri-scheme://test")

    @pytest.mark.asyncio
    async def test_server_stats_endpoint(
        self, sample_email_data, sample_analysis_data
    ):  # Renamed to avoid conflict
        """Test server stats functionality is updated when an email is processed and stored"""
        # This test now checks if stats are updated correctly.
        # In a real scenario, webhook processing would update stats.
        # Here, we simulate it.
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="stats-test-1",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
        )
        storage.email_storage["stats-test-1"] = processed_email
        # Manually update stats as if webhook.py processed it
        storage.stats.total_processed += 1
        storage.stats.avg_urgency_score = (
            storage.stats.avg_urgency_score * (storage.stats.total_processed - 1)
            + analysis.urgency_score
        ) / storage.stats.total_processed

        assert storage.stats.total_processed >= 1
        assert storage.stats.avg_urgency_score > 0

        result_str = await server.handle_read_resource("email://stats")
        data = json.loads(result_str)
        assert data["total_processed"] == 1
        assert data["avg_urgency_score"] == analysis.urgency_score

    @pytest.mark.asyncio
    async def test_server_with_processing_errors_resource(
        self, sample_email_data
    ):  # Renamed
        """Test server behavior when emails have processing errors via resource"""
        email_data_obj = EmailData(**sample_email_data)
        error_email = ProcessedEmail(
            id="error-1",
            email_data=email_data_obj,
            status=EmailStatus.ERROR,
            error_message="Processing failed due to invalid content",
        )
        storage.email_storage["error-1"] = error_email

        result_str = await server.handle_read_resource("email://processed/error-1")

        assert isinstance(result_str, str)
        data = json.loads(result_str)
        assert data["id"] == "error-1"
        assert data["status"] == "error"
        assert data["error_message"] == "Processing failed due to invalid content"


class TestToolHandling:
    """Test MCP tool handling"""

    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        # ... reset other stats fields ...
        server.storage = storage

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools"""
        tools_list = await server.handle_list_tools()  # Direct call

        assert isinstance(tools_list, list)
        assert len(tools_list) >= 4  # Base tools

        tool_names = [tool.name for tool in tools_list]
        expected_tools = [
            "analyze_email",
            "search_emails",
            "get_email_stats",
            "extract_tasks",
        ]

        # Real-time tools are available when REALTIME_AVAILABLE is True
        if server.REALTIME_AVAILABLE:
            realtime_tools = [
                "subscribe_to_email_changes",
                "get_realtime_stats",
                "manage_user_subscriptions",
                "monitor_ai_analysis",
            ]
            expected_tools.extend(realtime_tools)

        # Integration tools that are implemented
        if server.INTEGRATIONS_AVAILABLE:
            integration_tools = [
                "export_emails",
                "list_integrations",
                "process_through_plugins",
            ]
            expected_tools.extend(integration_tools)

        # If AI tools are available, add AI-powered tools
        if server.AI_TOOLS_AVAILABLE:
            ai_tools = [
                "ai_extract_tasks",
                "ai_analyze_context",
                "ai_summarize_thread",
                "ai_detect_urgency",
                "ai_suggest_response",
            ]
            expected_tools.extend(ai_tools)

        # Verify we have the expected tools
        assert len(tools_list) == len(expected_tools), f"Expected {len(expected_tools)} tools, got {len(tools_list)}"

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Expected tool '{tool_name}' not found in {tool_names}"

    @pytest.mark.asyncio
    async def test_analyze_email_tool_existing_email(
        self, sample_email_data, sample_analysis_data, monkeypatch
    ):
        """Test analyze_email tool with existing email"""
        # Setup test data with analysis
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="analyze-test",
            email_data=email_data,
            status=EmailStatus.ANALYZED,
            analysis=analysis,
        )
        storage.email_storage["analyze-test"] = processed_email

        # Mock the AI provider
        mock_ai_provider = MagicMock()
        mock_ai_provider.analyze_context.return_value = analysis

        # Patch the AI provider in the server module
        monkeypatch.setattr("src.server.ai_provider", mock_ai_provider)

        # Call the tool
        result_content_list = await server.handle_call_tool(
            "analyze_email", {"email_id": "analyze-test"}
        )

        # Verify the response
        assert isinstance(result_content_list, list)
        assert len(result_content_list) == 1
        assert isinstance(result_content_list[0], TextContent)

        response_data = json.loads(result_content_list[0].text)
        assert response_data["email_id"] == "analyze-test"
        assert response_data["urgency_score"] == 75
        assert response_data["urgency_level"] == "high"  # From fixture

        # Verify the AI provider was called correctly if needed
        # mock_ai_provider.analyze_context.assert_called_once_with(...)

    @pytest.mark.asyncio
    async def test_analyze_email_tool_content_analysis(self):
        """Test analyze_email tool with content analysis"""
        with patch("src.server.email_extractor") as mock_extractor:
            mock_metadata = MagicMock()
            mock_metadata.urgency_indicators = {
                "high": ["urgent", "asap"],
                "medium": [],
                "low": [],
            }
            mock_metadata.sentiment_indicators = {
                "positive": ["great"],
                "negative": [],
                "neutral": [],
            }
            mock_metadata.priority_keywords = ["important", "meeting"]
            mock_metadata.action_words = ["schedule", "review"]
            mock_metadata.temporal_references = ["tomorrow", "3pm"]
            mock_metadata.contact_info = {
                "email": ["john@example.com"],
                "phone": [],
                "url": [],
            }

            mock_extractor.extract_from_email.return_value = mock_metadata
            mock_extractor.calculate_urgency_score.return_value = (80, "high")

            result_content_list = await server.handle_call_tool(  # Direct call
                "analyze_email",
                {
                    "content": "This is an urgent email about an important meeting",
                    "subject": "Important Meeting",
                },
            )

            assert isinstance(result_content_list, list)
            assert len(result_content_list) == 1
            response_data = json.loads(result_content_list[0].text)
            assert "urgency_score" in response_data
            assert response_data["urgency_score"] == 80
            assert (
                "sentiment" in response_data
            )  # Default to "positive" due to mock logic

    @pytest.mark.asyncio
    async def test_analyze_email_tool_missing_params(self):
        """Test analyze_email tool with missing parameters"""
        result_content_list = await server.handle_call_tool(
            "analyze_email", {}
        )  # Direct call
        assert isinstance(result_content_list, list)
        assert len(result_content_list) == 1
        assert (
            "Error: Either email_id or content must be provided"
            in result_content_list[0].text
        )

    @pytest.mark.asyncio
    async def test_analyze_email_tool_non_existent_id(self):
        """Test analyze_email tool with a non-existent email_id."""
        result_content_list = await server.handle_call_tool(
            "analyze_email", {"email_id": "non-existent-id"}
        )
        assert isinstance(result_content_list, list)
        assert len(result_content_list) == 1
        # Based on the implementation, if email_id is not in storage, it will proceed to content analysis
        # which will fail if content is not provided.
        assert (
            "Error: Either email_id or content must be provided"
            in result_content_list[0].text
        )

    @pytest.mark.asyncio
    async def test_analyze_email_tool_existing_email_not_analyzed(
        self, sample_email_data
    ):
        """Test analyze_email tool with an existing email that has no analysis yet."""
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="not-analyzed-test",
            email_data=email_data,
            analysis=None,  # Explicitly no analysis
        )
        storage.email_storage["not-analyzed-test"] = processed_email

        result_content_list = await server.handle_call_tool(
            "analyze_email", {"email_id": "not-analyzed-test"}
        )
        assert isinstance(result_content_list, list)
        assert len(result_content_list) == 1
        assert (
            "Email not-analyzed-test found but not yet analyzed"
            in result_content_list[0].text
        )

    @pytest.mark.asyncio
    async def test_search_emails_tool(self, sample_email_data, sample_analysis_data):
        """Test search_emails tool"""
        email_configs = [
            ("search-1", "Meeting about project", UrgencyLevel.HIGH, "positive"),
            ("search-2", "Invoice payment due", UrgencyLevel.MEDIUM, "neutral"),
            ("search-3", "Project update meeting", UrgencyLevel.LOW, "positive"),
        ]

        for i, (email_id, subject, urgency, sentiment) in enumerate(email_configs):
            current_analysis_data = sample_analysis_data.copy()
            current_analysis_data["urgency_level"] = urgency
            current_analysis_data["sentiment"] = sentiment
            analysis = EmailAnalysis(**current_analysis_data)

            current_email_data = sample_email_data.copy()
            current_email_data["message_id"] = email_id
            current_email_data["subject"] = subject
            # Ensure text_body is set for search
            current_email_data["text_body"] = f"Content for {subject} {sentiment} email"
            email_data_obj = EmailData(**current_email_data)

            processed_email = ProcessedEmail(
                id=email_id, email_data=email_data_obj, analysis=analysis
            )
            storage.email_storage[email_id] = processed_email

        # Test search by query
        result_content_list = await server.handle_call_tool(
            "search_emails", {"query": "meeting"}
        )  # Direct call
        response_data = json.loads(result_content_list[0].text)
        assert (
            response_data["total_found"] == 2
        )  # "Meeting about project" and "Project update meeting"

        # Test search by urgency level
        result_content_list = await server.handle_call_tool(
            "search_emails", {"urgency_level": "high"}
        )  # Direct call
        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_found"] == 1

        # Test search with no results
        result_content_list = await server.handle_call_tool(
            "search_emails", {"query": "nonexistentquery"}
        )
        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_found"] == 0
        assert len(response_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_get_email_stats_tool(self, sample_email_data, sample_analysis_data):
        """Test get_email_stats tool"""
        for i in range(3):
            analysis = EmailAnalysis(**sample_analysis_data)  # Urgency score 75
            email_data_obj = EmailData(
                **{**sample_email_data, "message_id": f"stats-{i}"}
            )
            processed_email = ProcessedEmail(
                id=f"stats-{i}", email_data=email_data_obj, analysis=analysis
            )
            storage.email_storage[f"stats-{i}"] = processed_email
            storage.stats.total_processed += 1  # Simulate webhook processing

        storage.stats.processing_times = [0.1, 0.2, 0.15]

        # Update avg_urgency_score correctly
        if storage.stats.total_processed > 0:
            storage.stats.avg_urgency_score = sample_analysis_data["urgency_score"]

        result_content_list = await server.handle_call_tool(  # Direct call
            "get_email_stats", {"include_distribution": True}
        )

        assert isinstance(result_content_list, list)
        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_emails"] == 3
        assert response_data["analyzed_emails"] == 3
        assert "urgency_distribution" in response_data
        assert "sentiment_distribution" in response_data
        assert response_data["avg_urgency_score"] == pytest.approx(75.0)

    @pytest.mark.asyncio
    async def test_extract_tasks_tool_all_emails(
        self, sample_email_data, sample_analysis_data
    ):
        """Test extract_tasks tool for all emails"""
        urgency_scores = [30, 50, 70]
        for i, score in enumerate(urgency_scores):
            current_analysis_data = sample_analysis_data.copy()
            current_analysis_data["urgency_score"] = score
            current_analysis_data["action_items"] = [
                f"Task for score {score}"
            ]  # Ensure action items exist
            analysis = EmailAnalysis(**current_analysis_data)

            email_data_obj = EmailData(
                **{**sample_email_data, "message_id": f"extract-{i}"}
            )
            processed_email = ProcessedEmail(
                id=f"extract-{i}", email_data=email_data_obj, analysis=analysis
            )
            storage.email_storage[f"extract-{i}"] = processed_email

        result_content_list = await server.handle_call_tool(  # Direct call
            "extract_tasks", {"urgency_threshold": 40}
        )

        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_tasks"] == 2  # Emails with score 50 and 70
        assert response_data["urgency_threshold"] == 40
        assert (
            response_data["tasks"][0]["urgency_score"]
            >= response_data["tasks"][1]["urgency_score"]
        )

    @pytest.mark.asyncio
    async def test_extract_tasks_tool_specific_email(
        self, sample_email_data, sample_analysis_data
    ):
        """Test extract_tasks tool for specific email"""
        current_analysis_data = sample_analysis_data.copy()
        current_analysis_data["urgency_score"] = 80
        current_analysis_data["action_items"] = ["Review document", "Schedule meeting"]
        analysis = EmailAnalysis(**current_analysis_data)

        email_data_obj = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="specific-task", email_data=email_data_obj, analysis=analysis
        )
        storage.email_storage["specific-task"] = processed_email

        result_content_list = await server.handle_call_tool(  # Direct call
            "extract_tasks", {"email_id": "specific-task"}
        )

        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_tasks"] == 1
        assert response_data["tasks"][0]["email_id"] == "specific-task"
        assert len(response_data["tasks"][0]["action_items"]) == 2

    @pytest.mark.asyncio
    async def test_extract_tasks_tool_email_not_found(self):
        """Test extract_tasks tool when specific email_id does not exist."""
        result_content_list = await server.handle_call_tool(
            "extract_tasks", {"email_id": "non-existent-email"}
        )
        assert "Email non-existent-email not found" in result_content_list[0].text

    @pytest.mark.asyncio
    async def test_extract_tasks_tool_no_tasks_found(
        self, sample_email_data, sample_analysis_data
    ):
        """Test extract_tasks tool when an email has no action items or is below threshold."""
        # Email below threshold
        analysis_below_thresh = EmailAnalysis(
            **{**sample_analysis_data, "urgency_score": 30, "action_items": ["Task A"]}
        )
        email_below_thresh = ProcessedEmail(
            id="below-thresh",
            email_data=EmailData(**sample_email_data),
            analysis=analysis_below_thresh,
        )
        storage.email_storage["below-thresh"] = email_below_thresh

        # Email above threshold but no action items
        analysis_no_actions = EmailAnalysis(
            **{**sample_analysis_data, "urgency_score": 50, "action_items": []}
        )
        email_no_actions = ProcessedEmail(
            id="no-actions",
            email_data=EmailData(
                **{**sample_email_data, "message_id": "no-actions-msg"}
            ),
            analysis=analysis_no_actions,
        )
        storage.email_storage["no-actions"] = email_no_actions

        result_content_list = await server.handle_call_tool(
            "extract_tasks", {"urgency_threshold": 40}
        )
        response_data = json.loads(result_content_list[0].text)
        # Only the email with score 50 but no actions *might* appear if it passes threshold but has no tasks.
        # The current logic includes emails if analysis.urgency_score >= urgency_threshold,
        # then populates action_items. So an email with no action items but high urgency WILL be in the list.
        assert (
            response_data["total_tasks"] == 1
        )  # Only "no-actions" email (score 50 >= 40)
        assert response_data["tasks"][0]["email_id"] == "no-actions"
        assert len(response_data["tasks"][0]["action_items"]) == 0

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool"""
        with pytest.raises(
            ValueError, match="Unknown tool: unknown_tool_name"
        ):  # Adjusted match string
            await server.handle_call_tool("unknown_tool_name", {})  # Direct call

    @pytest.mark.skipif(
        not server.INTEGRATIONS_AVAILABLE, reason="Integrations not available"
    )
    @pytest.mark.asyncio
    async def test_export_emails_tool(self, sample_email_data):
        """Test export_emails tool if integrations are available."""
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(id="export-test", email_data=email_data)
        storage.email_storage["export-test"] = processed_email

        # Patch the DataExporter.export_emails method and the DataExporter.ExportFormat enum/callable
        with (
            patch("src.server.DataExporter.export_emails") as mock_export,
            patch(
                "src.server.DataExporter.ExportFormat",
                return_value=MagicMock(name="MockedExportFormatInstance"),
                create=True,  # Add create=True to ensure the attribute is created if missing
            ) as mock_export_format,
        ):
            mock_export.return_value = "exported_emails.json"  # Simulate successful export returning a filename

            result_content_list = await server.handle_call_tool(
                "export_emails",
                {"format": "json", "limit": 1, "filename": "test_export.json"},
            )
            response_data = json.loads(result_content_list[0].text)
            assert response_data["success"] is True
            assert response_data["exported_count"] == 1
            assert response_data["filename"] == "exported_emails.json"
            mock_export.assert_called_once()
            # Ensure ExportFormat was called with the correct format string
            mock_export_format.assert_called_once_with("json")

    @pytest.mark.skipif(
        not server.INTEGRATIONS_AVAILABLE, reason="Integrations not available"
    )
    @pytest.mark.asyncio
    async def test_list_integrations_tool(self):
        """Test list_integrations tool."""
        with patch("src.server.integration_registry") as mock_registry:
            mock_registry.list_integrations.return_value = {
                "databases": ["sqlite"],
                "ai_interfaces": [],
                "plugins": ["test_plugin"],
            }
            mock_registry.plugin_manager.get_plugin_info.return_value = {
                "test_plugin": {"version": "1.0"}
            }

            # Also patch the local import in the function
            with patch("src.server.integrations.integration_registry", mock_registry):
                result_content_list = await server.handle_call_tool(
                    "list_integrations", {}
                )
                response_data = json.loads(result_content_list[0].text)
                assert response_data["integrations_available"] is True
                assert "sqlite" in response_data["databases"]
                assert "test_plugin" in response_data["plugins"]["registered"]

    @pytest.mark.skipif(
        not server.INTEGRATIONS_AVAILABLE, reason="Integrations not available"
    )
    @pytest.mark.asyncio
    async def test_process_through_plugins_tool(
        self, sample_email_data, sample_analysis_data
    ):
        """Test process_through_plugins tool if integrations are available."""
        email_data = EmailData(**sample_email_data)

        # Initial state of the email in storage
        initial_analysis_dict = sample_analysis_data.copy()
        initial_analysis_dict["tags"] = ["initial_tag"]
        initial_analysis = EmailAnalysis(**initial_analysis_dict)
        original_email = ProcessedEmail(
            id="plugin-test", email_data=email_data, analysis=initial_analysis
        )
        storage.email_storage["plugin-test"] = original_email

        # Define the state of the email *after* mock plugin processing
        analysis_after_plugin_dict = sample_analysis_data.copy()
        analysis_after_plugin_dict["tags"] = ["initial_tag", "plugin_processed_tag"]
        # Ensure other fields are present if the EmailAnalysis model expects them
        analysis_after_plugin_dict.setdefault("urgency_score", 75)
        analysis_after_plugin_dict.setdefault("urgency_level", UrgencyLevel.HIGH)
        analysis_after_plugin_dict.setdefault("sentiment", "positive")

        mock_analysis_after_plugin = EmailAnalysis(**analysis_after_plugin_dict)

        mock_processed_email_by_plugin = ProcessedEmail(
            id="plugin-test",
            email_data=email_data,
            analysis=mock_analysis_after_plugin,
        )

        # Patch the actual plugin processing function and the list of plugins
        with (
            patch(
                "src.server.integration_registry.plugin_manager.process_email_through_plugins"
            ) as mock_process_plugins,
            patch(
                "src.server.integration_registry.plugin_manager.plugins",
                new=[MagicMock(name="MockPlugin1")],
            ),
        ):
            mock_process_plugins.return_value = mock_processed_email_by_plugin

            result_content_list = await server.handle_call_tool(
                "process_through_plugins", {"email_id": "plugin-test"}
            )
            response_data = json.loads(result_content_list[0].text)

            assert response_data["success"] is True
            assert response_data["email_id"] == "plugin-test"
            assert "plugin_processed_tag" in response_data["updated_tags"]
            assert "initial_tag" in response_data["updated_tags"]
            assert (
                response_data["plugins_applied"] == 1
            )  # Based on the mocked .plugins list


class TestPromptHandling:
    """Test MCP prompt handling"""

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing available prompts"""
        prompts_list = await server.handle_list_prompts()  # Direct call

        assert isinstance(prompts_list, list)
        assert len(prompts_list) == 1
        assert prompts_list[0].name == "email_analysis"

    @pytest.mark.asyncio
    async def test_get_email_analysis_prompt(self):
        """Test getting email analysis prompt"""
        prompt_message = await server.handle_get_prompt(  # Direct call
            "email_analysis",
            {"email_content": "This is a test email", "analysis_type": "urgency"},
        )

        assert isinstance(prompt_message, PromptMessage)
        assert prompt_message.role == "user"
        assert isinstance(prompt_message.content, TextContent)
        assert "urgency" in prompt_message.content.text
        assert "This is a test email" in prompt_message.content.text

    @pytest.mark.asyncio
    async def test_get_unknown_prompt(self):
        """Test getting unknown prompt"""
        with pytest.raises(
            ValueError, match="Unknown prompt: unknown_prompt_name"
        ):  # Adjusted match string
            await server.handle_get_prompt("unknown_prompt_name", {})  # Direct call


class TestErrorHandlingScenarios:  # Renamed from TestErrorHandling
    """Test error handling in server functions"""

    def setup_method(self):
        storage.email_storage.clear()
        # ... reset other stats ...
        server.storage = storage

    @pytest.mark.asyncio
    async def test_tool_error_handling_extract_tasks_nonexistent_email(
        self,
    ):  # More specific name
        """Test error handling in extract_tasks tool with non-existent email_id"""
        result_content_list = await server.handle_call_tool(
            "extract_tasks", {"email_id": "nonexistent-email-for-task"}
        )
        assert isinstance(result_content_list, list)
        assert (
            "Email nonexistent-email-for-task not found" in result_content_list[0].text
        )

    @pytest.mark.asyncio
    async def test_analyze_email_tool_general_exception(self):  # More specific name
        """Test error handling in analyze_email tool when email_extractor fails"""
        with patch("src.server.email_extractor.extract_from_email") as mock_extract:
            mock_extract.side_effect = Exception("Simulated analysis failure")
            result_content_list = await server.handle_call_tool(
                "analyze_email", {"content": "Test content that will fail"}
            )
            assert isinstance(result_content_list, list)
            assert (
                "Analysis error: Simulated analysis failure"
                in result_content_list[0].text
            )


class TestServerIntegrationScenarios:  # Renamed from TestServerIntegration
    """Test server integration scenarios"""

    def setup_method(self):
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        # ... reset other stats ...
        server.storage = storage

    @pytest.mark.asyncio
    async def test_complete_workflow(self, sample_email_data, sample_analysis_data):
        """Test complete workflow from resource listing to data access"""
        # 1. Store test data
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="workflow-test",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
        )
        storage.email_storage["workflow-test"] = processed_email
        storage.stats.total_processed = 1  # Simulate processing

        # 2. Test resource listing (includes the dynamic URI for the new email)
        resources = await server.handle_list_resources()
        resource_uris = [str(r.uri) for r in resources]
        assert "email://processed/workflow-test" in resource_uris

        # 3. Test tool listing
        tools = await server.handle_list_tools()
        assert len(tools) >= 4

        # 4. Test reading all processed emails resource
        result_str = await server.handle_read_resource("email://processed")
        data = json.loads(result_str)
        assert data["total_count"] == 1
        assert data["emails"][0]["id"] == "workflow-test"

        # 5. Test reading the specific email resource
        specific_email_str = await server.handle_read_resource(
            "email://processed/workflow-test"
        )
        specific_email_data = json.loads(specific_email_str)
        assert specific_email_data["id"] == "workflow-test"

        # 6. Test analyzing the stored email using analyze_email tool
        result_content_list = await server.handle_call_tool(
            "analyze_email", {"email_id": "workflow-test"}
        )
        response_data = json.loads(result_content_list[0].text)
        assert response_data["email_id"] == "workflow-test"
        assert response_data["urgency_score"] == sample_analysis_data["urgency_score"]

        # 7. Test searching for the email
        # Make sure the query matches something in the sample_email_data subject or body
        query_term = sample_email_data["subject"].split(" ")[0]  # e.g., "URGENT:"
        result_content_list = await server.handle_call_tool(
            "search_emails", {"query": query_term}
        )
        response_data = json.loads(result_content_list[0].text)
        assert response_data["total_found"] >= 1  # Should find at least the one email

    @pytest.mark.asyncio
    async def test_empty_storage_behavior(self):
        """Test server behavior with empty storage"""
        # Test reading resources with no data
        result_str = await server.handle_read_resource("email://processed")
        data = json.loads(result_str)
        assert data["total_count"] == 0
        assert data["emails"] == []

        result_str_analytics = await server.handle_read_resource("email://analytics")
        data_analytics = json.loads(result_str_analytics)
        assert data_analytics["message"] == "No emails processed yet"

        # Test tools with no data
        result_content_list_search = await server.handle_call_tool(
            "search_emails", {"query": "anything"}
        )
        response_data_search = json.loads(result_content_list_search[0].text)
        assert response_data_search["total_found"] == 0

        result_content_list_tasks = await server.handle_call_tool("extract_tasks", {})
        response_data_tasks = json.loads(result_content_list_tasks[0].text)
        assert response_data_tasks["total_tasks"] == 0
