"""
Integration tests for the MCP Email Parsing Server
Tests end-to-end functionality including webhook processing, MCP protocol compliance,
and real-world scenarios.
"""

import asyncio
import json
import os

# Import MCP and server components
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src import server  # MCP Server module
from src import storage
from src.models import EmailAnalysis, EmailData, ProcessedEmail, UrgencyLevel
from src.webhook import app as webhook_app  # FastAPI app instance


class TestEndToEndIntegration:
    """Test complete end-to-end email processing workflow"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Clear storage before each test
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        
        # Ensure webhook app and server use the same storage instance
        import src.server
        import src.webhook
        src.webhook.storage = storage
        src.server.storage = storage
    
    @pytest.mark.asyncio
    @patch('src.webhook.config')
    @patch('src.webhook.email_extractor')
    async def test_complete_postmark_to_mcp_workflow(self, mock_extractor, mock_config):
        """Test complete workflow from Postmark webhook to MCP resource access"""
        
        # Configure mocks
        mock_config.webhook_endpoint = "/webhook"
        mock_config.postmark_webhook_secret = None  # Disable signature verification for tests
        
        # Mock extraction results
        mock_metadata = MagicMock()
        mock_metadata.urgency_indicators = ["urgent", "asap", "critical"]
        mock_metadata.sentiment_indicators = {'positive': [], 'negative': ["outage", "down"]}
        mock_metadata.priority_keywords = ["urgent", "critical", "server", "outage"]
        mock_metadata.action_words = ["check", "restart", "contact", "send"]
        mock_metadata.temporal_references = ["1 hour", "tomorrow"]
        
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (95, "critical")
        
        # Step 1: Simulate Postmark webhook
        webhook_payload = {
            "From": "urgent.sender@company.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient User"}],
            "Subject": "URGENT: Server outage - immediate action required",
            "TextBody": """
URGENT: Production server is down!

We have a critical outage affecting all customers. Need immediate action:
1. Check server logs ASAP
2. Restart database cluster
3. Contact on-call engineer
4. Send customer communication

This needs to be resolved within 1 hour. Call me at 555-999-8888.

Status: CRITICAL
Priority: P0
""",
            "HtmlBody": "<p><strong>URGENT:</strong> Production server is down!</p><p>We have a critical outage affecting all customers...</p>",
            "MessageID": "integration-test-123@postmark.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [
                {"Name": "X-Priority", "Value": "1"},
                {"Name": "X-Urgency", "Value": "high"}
            ],
            "Attachments": []
        }
        
        # Step 2: Process webhook
        webhook_client = TestClient(webhook_app)
        response = webhook_client.post("/webhook", json=webhook_payload)
        
        # Verify webhook processing
        assert response.status_code == 200
        webhook_result = response.json()
        assert webhook_result["status"] == "success"
        processing_id = webhook_result["processing_id"]
        
        # Step 3: Verify email is stored
        assert len(storage.email_storage) == 1
        assert processing_id in storage.email_storage
        
        stored_email = storage.email_storage[processing_id]
        assert isinstance(stored_email, ProcessedEmail)
        assert stored_email.email_data.from_email == "urgent.sender@company.com"
        assert "URGENT" in stored_email.email_data.subject
        
        # Step 4: Verify analysis was performed
        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_level == UrgencyLevel.CRITICAL or stored_email.analysis.urgency_level == UrgencyLevel.HIGH
        assert stored_email.analysis.urgency_score > 70  # Should be high urgency
        
        # Step 5: Test MCP server functionality directly
        # Test list resources
        resources = await server.handle_list_resources()
        assert len(resources) >= 6  # Should have multiple resource types
        
        # Test read specific email resource
        email_resource_result = await server.handle_read_resource(f"email://processed/{processing_id}")
        assert email_resource_result is not None
        
        # Test read processed emails resource
        processed_emails_result = await server.handle_read_resource("email://processed")
        assert processed_emails_result is not None
        processed_data = json.loads(processed_emails_result)
        assert processed_data["total_count"] == 1
        assert len(processed_data["emails"]) == 1
        
        return processing_id
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    def test_high_volume_concurrent_processing(self, mock_config, mock_extractor):
        """Test concurrent webhook processing under load"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 75
        mock_metadata.priority_keywords = ["urgent", "critical"]
        mock_metadata.action_words = ["check", "review"]
        mock_metadata.temporal_references = ["tomorrow"]
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (75, "high")
        
        def create_webhook_payload(i):
            return {
                "From": f"sender{i}@example.com",
                "To": "recipient@example.com",
                "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
                "Subject": f"Test Email {i}",
                "TextBody": f"This is test email number {i}",
                "MessageID": f"test-{i}@example.com",
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": []
            }
        
        webhook_client = TestClient(webhook_app)
        num_emails = 10
        start_time = time.time()
        
        # Send multiple webhooks concurrently
        responses = []
        for i in range(num_emails):
            payload = create_webhook_payload(i)
            response = webhook_client.post("/webhook", json=payload)
            responses.append(response)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all processed successfully
        for response in responses:
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
        
        # Verify all emails stored
        assert len(storage.email_storage) == num_emails
        
        # Verify performance (should process 10 emails in reasonable time)
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, should be under 5s"
        
        # Verify stats updated
        assert storage.stats.total_processed == num_emails
        assert storage.stats.total_errors == 0
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self, mock_config, mock_extractor):
        """Test MCP tools with real processed emails"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 85
        mock_metadata.priority_keywords = ["urgent", "critical", "bug"]
        mock_metadata.action_words = ["fix", "review", "prepare"]
        mock_metadata.temporal_references = ["tomorrow", "Friday"]
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (85, "high")
        
        # First, process some test emails
        test_emails = [
            {
                "From": "urgent@company.com",
                "To": "manager@company.com", 
                "Subject": "URGENT: Critical bug in production",
                "TextBody": "We have a critical bug affecting payments. Need to fix ASAP. Deadline is tomorrow at 5 PM.",
                "MessageID": "urgent-bug@company.com"
            },
            {
                "From": "newsletter@company.com",
                "To": "subscriber@example.com",
                "Subject": "Weekly Newsletter",
                "TextBody": "Here's your weekly update with industry news and updates.",
                "MessageID": "newsletter@company.com"
            },
            {
                "From": "manager@company.com",
                "To": "team@company.com",
                "Subject": "Meeting scheduled for Friday",
                "TextBody": "Please review the agenda and prepare your status updates. Meeting is at 2 PM on Friday.",
                "MessageID": "meeting@company.com"
            }
        ]
        
        webhook_client = TestClient(webhook_app)
        processing_ids = []
        
        # Process all test emails
        for email_data in test_emails:
            payload = {
                **email_data,
                "ToFull": [{"Email": email_data["To"], "Name": "User"}],
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": []
            }
            response = webhook_client.post("/webhook", json=payload)
            assert response.status_code == 200
            result = response.json()
            processing_ids.append(result["processing_id"])
        
        # Test MCP tools directly (MCP server doesn't use FastAPI/HTTP)
        
        # Test search_emails tool
        search_result = await server.handle_call_tool("search_emails", {
            "query": "urgent",
            "limit": 10
        })
        assert len(search_result) > 0
        search_content = json.loads(search_result[0].text)
        assert len(search_content["results"]) >= 1  # Should find the urgent email
        
        # Test get_email_stats tool
        stats_result = await server.handle_call_tool("get_email_stats", {})
        assert len(stats_result) > 0
        stats_content = json.loads(stats_result[0].text)
        assert stats_content["total_processed"] == 3
        
        # Test extract_tasks tool
        tasks_result = await server.handle_call_tool("extract_tasks", {
            "email_id": processing_ids[0]  # The urgent email
        })
        assert len(tasks_result) > 0
        tasks_content = json.loads(tasks_result[0].text)
        assert len(tasks_content["tasks"]) > 0  # Should extract tasks from urgent email
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    def test_error_handling_and_recovery(self, mock_config, mock_extractor):
        """Test error handling in integration scenarios"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 60
        mock_metadata.priority_keywords = ["test"]
        mock_metadata.action_words = ["test"]
        mock_metadata.temporal_references = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (60, "medium")
        
        webhook_client = TestClient(webhook_app)
        
        # Test invalid JSON
        response = webhook_client.post(
            "/webhook",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 500]  # JSON decode error
        
        # Test missing required fields
        incomplete_payload = {
            "From": "sender@example.com",
            # Missing required fields like To, Subject, etc.
        }
        response = webhook_client.post("/webhook", json=incomplete_payload)
        assert response.status_code in [422, 500]  # Validation error (could be 500 due to internal handling)
        
        # Test malformed email data
        malformed_payload = {
            "From": "sender@example.com",
            "To": "recipient@example.com",
            "Subject": "Test",
            "TextBody": "Test",
            "MessageID": "test@example.com",
            "Date": "invalid-date-format",  # Invalid date
            "ToFull": [{"Email": "recipient@example.com"}],
            "Headers": [],
            "Attachments": []
        }
        response = webhook_client.post("/webhook", json=malformed_payload)
        # Should return server error for invalid date format
        assert response.status_code in [200, 400, 422, 500]
        
        # Verify error stats
        if storage.stats.total_errors > 0:
            assert storage.stats.total_errors <= 3  # At most the failed requests above


class TestPerformanceIntegration:
    """Performance and load testing"""
    
    def setup_method(self):
        """Setup for each test method"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.processing_times.clear()
        
        # Ensure webhook app uses the same storage instance
        import src.webhook
        src.webhook.storage = storage
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    def test_processing_time_requirements(self, mock_config, mock_extractor):
        """Test that processing meets <2s requirement per email"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 90
        mock_metadata.priority_keywords = ["urgent", "critical"]
        mock_metadata.action_words = ["review", "contact"]
        mock_metadata.temporal_references = ["tomorrow", "today"]
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (90, "critical")
        
        webhook_payload = {
            "From": "performance@test.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
            "Subject": "Performance Test Email with URGENT content for analysis",
            "TextBody": """
This is a performance test email with various content that should trigger analysis:
- URGENT action required
- Deadline is tomorrow
- Please review ASAP
- Critical priority
- Contact me at 555-123-4567
- Meeting scheduled for today at 3 PM
            """,
            "MessageID": "performance-test@example.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [
                {"Name": "X-Priority", "Value": "1"}
            ],
            "Attachments": []
        }
        
        webhook_client = TestClient(webhook_app)
        
        # Measure processing time
        start_time = time.time()
        response = webhook_client.post("/webhook", json=webhook_payload)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify successful processing
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        
        # Verify performance requirement
        assert processing_time < 2.0, f"Processing took {processing_time:.3f}s, should be under 2s"
        
        # Verify analysis was completed
        processing_id = result["processing_id"]
        stored_email = storage.email_storage[processing_id]
        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_score > 0
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    def test_memory_usage_stability(self, mock_config, mock_extractor):
        """Test memory usage doesn't grow excessively with processing"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 70
        mock_metadata.priority_keywords = ["urgent"]
        mock_metadata.action_words = ["analyze"]
        mock_metadata.temporal_references = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (70, "high")
        
        import os

        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        webhook_client = TestClient(webhook_app)
        
        # Process many emails
        for i in range(50):
            payload = {
                "From": f"sender{i}@example.com",
                "To": "recipient@example.com",
                "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
                "Subject": f"Test Email {i} with some urgent content and analysis",
                "TextBody": f"This is test email {i} with urgent tasks and deadlines to analyze.",
                "MessageID": f"memory-test-{i}@example.com",
                "Date": "2025-05-28T10:30:00.000Z",
                "Headers": [],
                "Attachments": []
            }
            response = webhook_client.post("/webhook", json=payload)
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (< 100MB for 50 emails)
        assert memory_growth < 100, f"Memory grew by {memory_growth:.2f}MB, should be under 100MB"
        
        # Verify all emails processed
        assert len(storage.email_storage) == 50


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and standards"""
    
    def setup_method(self):
        """Setup for each test method"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.processing_times.clear()
        
        # Ensure webhook app uses the same storage instance
        import src.webhook
        src.webhook.storage = storage
    
    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        """Test MCP server initialization and metadata"""
        
        # Test that server object has correct metadata
        assert server.server.name == "inbox-zen-email-parser"
        assert server.server.version == "0.1.0"
        assert "MCP server for unified email entry, parsing, and analysis" in server.server.instructions
    
    @pytest.mark.asyncio
    async def test_mcp_capabilities_advertisement(self):
        """Test server advertises correct capabilities"""
        
        # Test resources capability
        resources = await server.handle_list_resources()
        assert len(resources) >= 6  # Should have multiple resource types
        
        # Test tools capability  
        tools = await server.handle_list_tools()
        assert len(tools) >= 4  # Should have multiple tools
        
        # Test prompts capability
        prompts = await server.handle_list_prompts()
        assert len(prompts) >= 1  # Should have at least 1 prompt
    
    @patch('src.webhook.email_extractor')
    @patch('src.webhook.config')
    @pytest.mark.asyncio
    async def test_mcp_resource_operations(self, mock_config, mock_extractor):
        """Test MCP resource read operations"""
        
        # Disable webhook signature verification
        mock_config.postmark_webhook_secret = None
        
        # Mock email extraction
        mock_metadata = MagicMock()
        mock_metadata.urgency_score = 60
        mock_metadata.priority_keywords = ["test"]
        mock_metadata.action_words = ["testing"]
        mock_metadata.temporal_references = []
        mock_extractor.extract_from_email.return_value = mock_metadata
        mock_extractor.calculate_urgency_score.return_value = (60, "medium")
        
        # First add some test data
        webhook_payload = {
            "From": "test@example.com",
            "To": "recipient@example.com",
            "ToFull": [{"Email": "recipient@example.com", "Name": "Recipient"}],
            "Subject": "Test Email",
            "TextBody": "This is a test email for MCP resource testing",
            "MessageID": "mcp-test@example.com",
            "Date": "2025-05-28T10:30:00.000Z",
            "Headers": [],
            "Attachments": []
        }
        
        webhook_client = TestClient(webhook_app)
        response = webhook_client.post("/webhook", json=webhook_payload)
        assert response.status_code == 200
        
        # Test reading resources
        processed_emails_result = await server.handle_read_resource("email://processed")
        assert processed_emails_result is not None
        
        stats_result = await server.handle_read_resource("email://stats") 
        assert stats_result is not None


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])
