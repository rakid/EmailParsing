"""Unit tests for server.py - MCP Email Parsing Server"""

import pytest
import asyncio
import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from mcp.types import Resource, Tool, TextContent, Prompt, PromptMessage

# Add src directory to path for imports (same as server.py)
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Import server module and dependencies using same pattern as server.py
from src import server
import storage
from models import ProcessedEmail, EmailData, EmailAnalysis, EmailStatus, UrgencyLevel


class TestServerInitialization:
    """Test MCP server initialization"""
    
    def test_server_instance_exists(self):
        """Test that server instance is created"""
        assert server.server is not None
        assert hasattr(server.server, 'name')
        assert hasattr(server.server, 'version')
    
    def test_server_metadata(self):
        """Test server metadata configuration"""
        # Note: We can't directly test server.name/version without running the server
        # but we can verify the server instance exists and has the right structure
        assert server.server is not None


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
        import src.server
        src.server.storage = storage
    
    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing available resources"""
        # Note: The server has duplicate @server.list_resources() decorators
        # We'll test the behavior that should exist
        resources = await server.handle_list_resources()
        
        assert isinstance(resources, list)
        assert len(resources) >= 6  # At least the main 6 resources
        
        # Check for main resources
        resource_uris = [str(r.uri) for r in resources]
        expected_uris = [
            "email://processed",
            "email://stats", 
            "email://recent",
            "email://analytics",
            "email://high-urgency",
            "email://tasks"
        ]
        
        for uri in expected_uris:
            assert uri in resource_uris
    
    @pytest.mark.asyncio
    async def test_read_processed_emails_resource(self, sample_email_data, sample_analysis_data):
        """Test reading processed emails resource"""
        print(f"TEST: Starting test, storage length: {len(storage.email_storage)}")
        
        # Store a test email
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="test-email-1",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED
        )
        storage.email_storage["test-email-1"] = processed_email
        
        print(f"TEST: After adding email, storage length: {len(storage.email_storage)}")
        print(f"TEST: Storage keys: {list(storage.email_storage.keys())}")
        
        # Read the resource
        result = await server.handle_read_resource("email://processed")
        
        print(f"TEST: Server result type: {type(result)}")
        if isinstance(result, str):
            data = json.loads(result)
            print(f"TEST: Server total_count: {data.get('total_count', 'NOT FOUND')}")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "total_count" in data
        assert "emails" in data
        assert data["total_count"] == 1
        assert len(data["emails"]) == 1
        assert data["emails"][0]["id"] == "test-email-1"
    
    @pytest.mark.asyncio
    async def test_read_stats_resource(self):
        """Test reading email statistics resource"""
        # Update stats
        storage.stats.total_processed = 5
        storage.stats.total_errors = 1
        storage.stats.avg_urgency_score = 65.5
        
        result = await server.handle_read_resource("email://stats")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["total_processed"] == 5
        assert data["total_errors"] == 1
        assert data["avg_urgency_score"] == 65.5
    
    @pytest.mark.asyncio
    async def test_read_recent_emails_resource(self, sample_email_data):
        """Test reading recent emails resource"""
        # Store multiple emails
        for i in range(15):  # More than the default limit of 10
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"recent-{i}",
                "received_at": datetime.now()
            })
            processed_email = ProcessedEmail(
                id=f"recent-{i}",
                email_data=email_data
            )
            storage.email_storage[f"recent-{i}"] = processed_email
        
        result = await server.handle_read_resource("email://recent")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "count" in data
        assert "emails" in data
        assert data["count"] <= 10  # Should be limited to 10
    
    @pytest.mark.asyncio
    async def test_read_analytics_resource(self, sample_email_data, sample_analysis_data):
        """Test reading analytics resource"""
        # Store emails with different urgency levels
        urgency_levels = [UrgencyLevel.LOW, UrgencyLevel.MEDIUM, UrgencyLevel.HIGH]
        for i, level in enumerate(urgency_levels):
            analysis_data = {
                **sample_analysis_data,
                "urgency_level": level,
                "urgency_score": 25 + (i * 25)  # 25, 50, 75
            }
            analysis = EmailAnalysis(**analysis_data)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"analytics-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"analytics-{i}",
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[f"analytics-{i}"] = processed_email
        
        result = await server.handle_read_resource("email://analytics")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "total_emails" in data
        assert "urgency_distribution" in data
        assert "sentiment_distribution" in data
        assert data["total_emails"] == 3
    
    @pytest.mark.asyncio
    async def test_read_high_urgency_resource(self, sample_email_data, sample_analysis_data):
        """Test reading high urgency emails resource"""
        # Store emails with different urgency levels
        urgency_configs = [
            ("low-1", UrgencyLevel.LOW, 20),
            ("high-1", UrgencyLevel.HIGH, 80),
            ("medium-1", UrgencyLevel.MEDIUM, 50),
            ("high-2", UrgencyLevel.HIGH, 90)
        ]
        
        for email_id, urgency_level, urgency_score in urgency_configs:
            analysis_data = {
                **sample_analysis_data,
                "urgency_level": urgency_level,
                "urgency_score": urgency_score
            }
            analysis = EmailAnalysis(**analysis_data)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": email_id
            })
            processed_email = ProcessedEmail(
                id=email_id,
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[email_id] = processed_email
        
        result = await server.handle_read_resource("email://high-urgency")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "count" in data
        assert "emails" in data
        assert data["count"] == 2  # Only 2 high urgency emails
        assert len(data["emails"]) == 2
    
    @pytest.mark.asyncio
    async def test_read_tasks_resource(self, sample_email_data, sample_analysis_data):
        """Test reading tasks resource"""
        # Store emails with different urgency scores (above and below threshold)
        urgency_scores = [30, 50, 70]  # Only 50 and 70 should be included (>= 40)
        for i, score in enumerate(urgency_scores):
            analysis_data = {
                **sample_analysis_data,
                "urgency_score": score,
                "action_items": [f"Task {i}"]
            }
            analysis = EmailAnalysis(**analysis_data)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"task-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"task-{i}",
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[f"task-{i}"] = processed_email
        
        result = await server.handle_read_resource("email://tasks")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "total_tasks" in data
        assert "tasks" in data
        assert data["urgency_threshold"] == 40
        assert data["total_tasks"] == 2  # Only scores >= 40
    
    @pytest.mark.asyncio
    async def test_read_specific_email_resource(self, sample_email_data, sample_analysis_data):
        """Test reading specific email resource"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="specific-email",
            email_data=email_data,
            analysis=analysis
        )
        storage.email_storage["specific-email"] = processed_email
        
        result = await server.handle_read_resource("email://processed/specific-email")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["id"] == "specific-email"
        assert "resource_info" in data
        assert data["resource_info"]["email_id"] == "specific-email"
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self):
        """Test reading non-existent resource"""
        with pytest.raises(ValueError, match="Unknown resource"):
            await server.handle_read_resource("email://nonexistent")
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_email(self):
        """Test reading non-existent specific email"""
        with pytest.raises(ValueError, match="Email not found"):
            await server.handle_read_resource("email://processed/nonexistent-id")


class TestToolHandling:
    """Test MCP tool handling"""
    
    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        
        # Ensure server module uses the same storage instance
        import src.server
        src.server.storage = storage
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools"""
        tools = await server.handle_list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 7  # Expected number of tools
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "analyze_email",
            "search_emails", 
            "get_email_stats",
            "extract_tasks",
            "export_emails",
            "list_integrations",
            "process_through_plugins"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names
    
    @pytest.mark.asyncio
    async def test_analyze_email_tool_existing_email(self, sample_email_data, sample_analysis_data):
        """Test analyze_email tool with existing email"""
        # Store an analyzed email
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="analyze-test",
            email_data=email_data,
            analysis=analysis
        )
        storage.email_storage["analyze-test"] = processed_email
        
        result = await server.handle_call_tool("analyze_email", {"email_id": "analyze-test"})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        response_data = json.loads(result[0].text)
        assert response_data["email_id"] == "analyze-test"
        assert response_data["urgency_score"] == 75
        assert response_data["urgency_level"] == "high"
    
    @pytest.mark.asyncio
    async def test_analyze_email_tool_content_analysis(self):
        """Test analyze_email tool with content analysis"""
        # Mock the email_extractor to avoid complex dependencies
        with patch('src.server.email_extractor') as mock_extractor:
            # Set up mock
            mock_metadata = MagicMock()
            mock_metadata.urgency_indicators = ["urgent", "asap"]
            mock_metadata.sentiment_indicators = {'positive': ["great"], 'negative': []}
            mock_metadata.priority_keywords = ["important", "meeting"]
            mock_metadata.action_words = ["schedule", "review"]
            mock_metadata.temporal_references = ["tomorrow", "3pm"]
            mock_metadata.contact_info = ["john@example.com"]
            
            mock_extractor.extract_from_email.return_value = mock_metadata
            mock_extractor.calculate_urgency_score.return_value = (80, "high")
            
            result = await server.handle_call_tool("analyze_email", {
                "content": "This is an urgent email about an important meeting",
                "subject": "Important Meeting"
            })
            
            assert isinstance(result, list)
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert "urgency_score" in response_data
            assert "sentiment" in response_data
    
    @pytest.mark.asyncio
    async def test_analyze_email_tool_missing_params(self):
        """Test analyze_email tool with missing parameters"""
        result = await server.handle_call_tool("analyze_email", {})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert "Either email_id or content must be provided" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_emails_tool(self, sample_email_data, sample_analysis_data):
        """Test search_emails tool"""
        # Store emails with different properties and text bodies
        email_configs = [
            ("search-1", "Meeting about project", UrgencyLevel.HIGH, "positive", "We need to discuss the project in our meeting."),
            ("search-2", "Invoice payment due", UrgencyLevel.MEDIUM, "neutral", "Please process the invoice payment by end of week."),
            ("search-3", "Project update meeting", UrgencyLevel.LOW, "positive", "The team meeting went well and we made good progress.")
        ]
        
        for email_id, subject, urgency, sentiment, text_body in email_configs:
            analysis_data = {
                **sample_analysis_data,
                "urgency_level": urgency,
                "sentiment": sentiment
            }
            analysis = EmailAnalysis(**analysis_data)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": email_id,
                "subject": subject,
                "text_body": text_body  # Use specific text body without conflicting content
            })
            processed_email = ProcessedEmail(
                id=email_id,
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[email_id] = processed_email
        
        # Test search by query
        result = await server.handle_call_tool("search_emails", {"query": "meeting"})
        response_data = json.loads(result[0].text)
        assert response_data["total_found"] == 2  # Two emails contain "meeting"
        
        # Test search by urgency level
        result = await server.handle_call_tool("search_emails", {"urgency_level": "high"})
        response_data = json.loads(result[0].text)
        assert response_data["total_found"] == 1
        
        # Test search by sentiment
        result = await server.handle_call_tool("search_emails", {"sentiment": "positive"})
        response_data = json.loads(result[0].text)
        assert response_data["total_found"] == 2
    
    @pytest.mark.asyncio
    async def test_get_email_stats_tool(self, sample_email_data, sample_analysis_data):
        """Test get_email_stats tool"""
        # Store some emails with analysis
        for i in range(3):
            analysis = EmailAnalysis(**sample_analysis_data)
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"stats-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"stats-{i}",
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[f"stats-{i}"] = processed_email
        
        # Update stats
        storage.stats.total_processed = 3
        storage.stats.processing_times = [0.1, 0.2, 0.15]
        
        result = await server.handle_call_tool("get_email_stats", {"include_distribution": True})
        
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["total_emails"] == 3
        assert response_data["analyzed_emails"] == 3
        assert "urgency_distribution" in response_data
        assert "sentiment_distribution" in response_data
    
    @pytest.mark.asyncio
    async def test_extract_tasks_tool_all_emails(self, sample_email_data, sample_analysis_data):
        """Test extract_tasks tool for all emails"""
        # Store emails with different urgency scores
        urgency_scores = [30, 50, 70]  # Only 50 and 70 should be included
        for i, score in enumerate(urgency_scores):
            analysis_data = {
                **sample_analysis_data,
                "urgency_score": score,
                "action_items": [f"Task {i}"]
            }
            analysis = EmailAnalysis(**analysis_data)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"extract-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"extract-{i}",
                email_data=email_data,
                analysis=analysis
            )
            storage.email_storage[f"extract-{i}"] = processed_email
        
        result = await server.handle_call_tool("extract_tasks", {"urgency_threshold": 40})
        
        response_data = json.loads(result[0].text)
        assert response_data["total_tasks"] == 2
        assert response_data["urgency_threshold"] == 40
        # Tasks should be sorted by urgency score (highest first)
        assert response_data["tasks"][0]["urgency_score"] >= response_data["tasks"][1]["urgency_score"]
    
    @pytest.mark.asyncio
    async def test_extract_tasks_tool_specific_email(self, sample_email_data, sample_analysis_data):
        """Test extract_tasks tool for specific email"""
        analysis = EmailAnalysis(**{
            **sample_analysis_data,
            "urgency_score": 80,
            "action_items": ["Review document", "Schedule meeting"]
        })
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="specific-task",
            email_data=email_data,
            analysis=analysis
        )
        storage.email_storage["specific-task"] = processed_email
        
        result = await server.handle_call_tool("extract_tasks", {"email_id": "specific-task"})
        
        response_data = json.loads(result[0].text)
        assert response_data["total_tasks"] == 1
        assert response_data["tasks"][0]["email_id"] == "specific-task"
        assert len(response_data["tasks"][0]["action_items"]) == 2
    
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.handle_call_tool("unknown_tool", {})


class TestPromptHandling:
    """Test MCP prompt handling"""
    
    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing available prompts"""
        prompts = await server.handle_list_prompts()
        
        assert isinstance(prompts, list)
        assert len(prompts) == 1
        assert prompts[0].name == "email_analysis"
    
    @pytest.mark.asyncio
    async def test_get_email_analysis_prompt(self):
        """Test getting email analysis prompt"""
        result = await server.handle_get_prompt("email_analysis", {
            "email_content": "This is a test email",
            "analysis_type": "urgency"
        })
        
        assert isinstance(result, PromptMessage)
        assert result.role == "user"
        assert isinstance(result.content, TextContent)
        assert "urgency" in result.content.text
        assert "This is a test email" in result.content.text
    
    @pytest.mark.asyncio
    async def test_get_unknown_prompt(self):
        """Test getting unknown prompt"""
        with pytest.raises(ValueError, match="Unknown prompt"):
            await server.handle_get_prompt("unknown_prompt", {})


class TestErrorHandling:
    """Test error handling in server functions"""
    
    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        
        # Ensure server module uses the same storage instance
        import src.server
        src.server.storage = storage
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling in tool calls"""
        # Test with invalid email_id
        result = await server.handle_call_tool("extract_tasks", {"email_id": "nonexistent"})
        
        assert isinstance(result, list)
        assert "not found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_analysis_error_handling(self):
        """Test error handling in analysis tool"""
        # Mock email_extractor to raise an exception
        with patch('src.server.email_extractor') as mock_extractor:
            mock_extractor.extract_from_email.side_effect = Exception("Analysis failed")
            
            result = await server.handle_call_tool("analyze_email", {
                "content": "Test content"
            })
            
            assert isinstance(result, list)
            assert "Analysis error" in result[0].text


class TestServerIntegration:
    """Test server integration scenarios"""
    
    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats.total_processed = 0
        storage.stats.total_errors = 0
        storage.stats.avg_urgency_score = 0.0
        storage.stats.last_processed = None
        storage.stats.processing_times.clear()
        
        # Ensure server module uses the same storage instance
        import src.server
        src.server.storage = storage
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, sample_email_data, sample_analysis_data):
        """Test complete workflow from resource listing to data access"""
        # Store test data
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        processed_email = ProcessedEmail(
            id="workflow-test",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED
        )
        storage.email_storage["workflow-test"] = processed_email
        storage.stats.total_processed = 1
        
        # Test resource listing
        resources = await server.handle_list_resources()
        assert len(resources) >= 6
        
        # Test tool listing
        tools = await server.handle_list_tools()
        assert len(tools) == 7
        
        # Test reading processed emails
        result = await server.handle_read_resource("email://processed")
        data = json.loads(result)
        assert data["total_count"] == 1
        
        # Test analyzing the stored email
        result = await server.handle_call_tool("analyze_email", {"email_id": "workflow-test"})
        response_data = json.loads(result[0].text)
        assert response_data["email_id"] == "workflow-test"
        
        # Test searching for the email
        result = await server.handle_call_tool("search_emails", {"query": "URGENT"})
        response_data = json.loads(result[0].text)
        assert response_data["total_found"] == 1
    
    @pytest.mark.asyncio 
    async def test_empty_storage_behavior(self):
        """Test server behavior with empty storage"""
        # Test reading resources with no data
        result = await server.handle_read_resource("email://processed")
        data = json.loads(result)
        assert data["total_count"] == 0
        assert data["emails"] == []
        
        # Test tools with no data
        result = await server.handle_call_tool("search_emails", {"query": "anything"})
        response_data = json.loads(result[0].text)
        assert response_data["total_found"] == 0
        
        result = await server.handle_call_tool("extract_tasks", {})
        response_data = json.loads(result[0].text)
        assert response_data["total_tasks"] == 0
