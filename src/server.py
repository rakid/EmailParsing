# MCP Email Parsing Server - Foundation
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Type

from mcp.server import Server
from mcp.types import (
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

from . import storage
from .config import config
from .extraction import email_extractor

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Initialize placeholders for integration components and availability flag
DataExporter: Optional[Type[Any]] = None
integration_registry: Optional[Any] = None
integrations: Optional[Any] = None  # This will hold the imported 'integrations' module
ExportFormat: Optional[Type[Any]] = None
INTEGRATIONS_AVAILABLE = False  # Default to False

# Import integration capabilities
try:
    from . import integrations as _ImportedIntegrationsModule
    from .integrations import DataExporter as _ImportedDataExporter
    from .integrations import ExportFormat as _ImportedExportFormat
    from .integrations import integration_registry as _ImportedIntegrationRegistry

    DataExporter = _ImportedDataExporter
    # Attach ExportFormat as an attribute of DataExporter for test compatibility
    DataExporter.ExportFormat = _ImportedExportFormat  # type: ignore[attr-defined]
    ExportFormat = _ImportedExportFormat
    integration_registry = _ImportedIntegrationRegistry
    integrations = _ImportedIntegrationsModule

    INTEGRATIONS_AVAILABLE = True
    # print("✅ Integration module loaded successfully.") # Optional: for debugging
except ImportError:
    # DataExporter, integration_registry, integrations remain None as initialized
    # INTEGRATIONS_AVAILABLE remains False as initialized
    ExportFormat = None
    print(
        "⚠️ Integration module not available - running in basic mode. Integration features will be disabled."
    )

# Initialize MCP server with metadata
server: Server = Server(
    name=config.server_name,
    version=config.server_version,
    instructions=(
        "MCP server for unified email entry, parsing, and analysis for "
        "Inbox Zen application. Receives Postmark webhooks and performs "
        "intelligent email analysis."
    ),
)


# Server capabilities and initialization
@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available email resources with proper MCP schema"""
    return [
        Resource(
            uri=AnyUrl("email://processed"),
            name="Processed Emails",
            description="Access to all processed email data with analysis results",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("email://stats"),
            name="Email Statistics",
            description="Real-time email processing statistics and analytics",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("email://recent"),
            name="Recent Emails",
            description="Last 10 processed emails with analysis",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("email://analytics"),
            name="Email Analytics",
            description="Comprehensive analytics and distribution data",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("email://high-urgency"),
            name="High Urgency Emails",
            description="Emails marked as high urgency requiring immediate attention",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("email://tasks"),
            name="Email Tasks",
            description="Extracted tasks and action items from emails",
            mimeType="application/json",
        ),
    ] + [
        Resource(
            uri=AnyUrl(f"email://processed/{email_id}"),
            name=f"Email {email_id[:8]}...",
            description=f"Individual email data and analysis for {email_id}",
            mimeType="application/json",
        )
        for email_id in list(storage.email_storage.keys())[
            :10
        ]  # Limit to recent emails
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read email resource content with proper data formatting and pagination"""
    if uri == "email://processed":
        # Return all processed emails with pagination info
        emails_data = {
            "total_count": len(storage.email_storage),
            "emails": [email.model_dump() for email in storage.email_storage.values()],
            "resource_info": {
                "uri": uri,
                "last_updated": datetime.now().isoformat(),
                "supports_pagination": True,
            },
        }
        return json.dumps(emails_data, indent=2, default=str)

    elif uri == "email://stats":
        # Return current statistics with additional metadata
        stats_data = storage.stats.model_dump()
        stats_data["total_emails_in_storage"] = len(storage.email_storage)
        stats_data["resource_info"] = {
            "uri": uri,
            "generated_at": datetime.now().isoformat(),
            "total_emails_in_storage": len(storage.email_storage),
        }
        return json.dumps(stats_data, indent=2, default=str)

    elif uri == "email://recent":
        # Return last 10 emails, sorted by processed_at or received_at
        all_emails = list(storage.email_storage.values())
        # Sort by processed_at (most recent first), fall back to received_at
        all_emails.sort(
            key=lambda x: x.processed_at or x.email_data.received_at, reverse=True
        )
        recent_emails = all_emails[:10]
        return json.dumps(
            {
                "count": len(recent_emails),
                "emails": [email.model_dump() for email in recent_emails],
                "resource_info": {
                    "uri": uri,
                    "limit": 10,
                    "total_available": len(storage.email_storage),
                },
            },
            indent=2,
            default=str,
        )

    elif uri == "email://analytics":
        # Return comprehensive analytics
        if not storage.email_storage:
            return json.dumps({"message": "No emails processed yet"})

        emails_with_analysis = [e for e in storage.email_storage.values() if e.analysis]

        if not emails_with_analysis:
            return json.dumps({"message": "No analyzed emails found"})

        # Calculate distributions
        urgency_dist = {"low": 0, "medium": 0, "high": 0}
        sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0}
        urgency_scores = []

        for email in emails_with_analysis:
            if email.analysis:  # Additional None check for mypy
                urgency_dist[email.analysis.urgency_level.value] += 1
                sentiment_dist[email.analysis.sentiment] += 1
                urgency_scores.append(email.analysis.urgency_score)

        analytics_data = {
            "total_emails": len(storage.email_storage),
            "analyzed_emails": len(emails_with_analysis),
            "urgency_distribution": urgency_dist,
            "sentiment_distribution": sentiment_dist,
            "urgency_stats": {
                "average": sum(urgency_scores) / len(urgency_scores),
                "max": max(urgency_scores),
                "min": min(urgency_scores),
            },
            "resource_info": {"uri": uri, "generated_at": datetime.now().isoformat()},
        }
        return json.dumps(analytics_data, indent=2)

    elif uri == "email://high-urgency":
        # Return only high urgency emails
        high_urgency_emails = [
            email
            for email in storage.email_storage.values()
            if email.analysis and email.analysis.urgency_level.value == "high"
        ]

        return json.dumps(
            {
                "count": len(high_urgency_emails),
                "emails": [email.model_dump() for email in high_urgency_emails],
                "resource_info": {
                    "uri": uri,
                    "filter": "urgency_level=high",
                    "total_high_urgency": len(high_urgency_emails),
                },
            },
            indent=2,
            default=str,
        )

    elif uri == "email://tasks":
        # Return extracted tasks from all emails
        tasks: list[Dict[str, Any]] = []
        for email in storage.email_storage.values():
            if (
                email.analysis and email.analysis.urgency_score >= 40
            ):  # Default threshold
                task_data = {
                    "email_id": email.id,
                    "from": email.email_data.from_email,
                    "subject": email.email_data.subject,
                    "urgency_score": email.analysis.urgency_score,
                    "action_items": email.analysis.action_items,
                    "temporal_references": email.analysis.temporal_references,
                    "priority": email.analysis.urgency_level.value,
                    "received_at": email.email_data.received_at.isoformat(),
                }
                tasks.append(task_data)

        # Sort by urgency score
        tasks.sort(key=lambda x: int(x.get("urgency_score", 0)), reverse=True)

        return json.dumps(
            {
                "total_tasks": len(tasks),
                "urgency_threshold": 40,
                "tasks": tasks,
                "resource_info": {
                    "uri": uri,
                    "generated_at": datetime.now().isoformat(),
                },
            },
            indent=2,
        )

    elif uri.startswith("email://processed/"):
        # Return specific email
        email_id = uri.replace("email://processed/", "")
        if email_id in storage.email_storage:
            email_data = storage.email_storage[email_id].model_dump()
            email_data["resource_info"] = {
                "uri": uri,
                "email_id": email_id,
                "accessed_at": datetime.now().isoformat(),
            }
            return json.dumps(email_data, indent=2, default=str)
        else:
            raise ValueError(f"Email not found: {email_id}")

    else:
        raise ValueError(f"Unknown resource: {uri}")


# --- Tool Handlers ---
# Refactor: Use a dictionary to map tool names to handler functions


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available email analysis tools"""
    tools = [
        Tool(
            name="analyze_email",
            description=(
                "Analyze email content for urgency, sentiment, and metadata "
                "using regex patterns"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": (
                            "Email ID to analyze (optional, will use content "
                            "if not provided)"
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Email content to analyze (required if email_id "
                            "not provided)"
                        ),
                    },
                    "subject": {
                        "type": "string",
                        "description": (
                            "Email subject line (optional, enhances analysis)"
                        ),
                    },
                },
                "anyOf": [{"required": ["email_id"]}, {"required": ["content"]}],
            },
        ),
        Tool(
            name="search_emails",
            description="Search and filter processed emails by various criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against email content",
                    },
                    "urgency_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Filter by urgency level",
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"],
                        "description": "Filter by sentiment",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                        "description": ("Maximum number of results to return"),
                    },
                },
            },
        ),
        Tool(
            name="get_email_stats",
            description="Get comprehensive statistics about processed emails",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_distribution": {
                        "type": "boolean",
                        "default": True,
                        "description": (
                            "Include urgency and sentiment distribution data"
                        ),
                    }
                },
            },
        ),
        Tool(
            name="extract_tasks",
            description=("Extract action items and tasks from emails"),
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": ("Specific email ID to extract tasks from"),
                    },
                    "urgency_threshold": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 40,
                        "description": (
                            "Minimum urgency score to consider for task " "extraction"
                        ),
                    },
                },
            },
        ),
    ] + (
        # Conditionally add integration tools
        [
            # Data Export Tool
            Tool(
                name="export_emails",
                description=(
                    "Export processed emails in various formats for AI "
                    "analysis or database storage"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "enum": ["json", "csv", "jsonl", "parquet"],
                            "description": "Export format for the data",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "description": ("Maximum number of emails to export"),
                        },
                        "filename": {
                            "type": "string",
                            "description": ("Output filename (optional)"),
                        },
                    },
                    "required": ["format"],
                },
            ),
            # List Integrations Tool
            Tool(
                name="list_integrations",
                description=(
                    "List all available integrations (databases, AI interfaces, "
                    "plugins)"
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            # Process through Plugins Tool
            Tool(
                name="process_through_plugins",
                description=(
                    "Process an email through all registered plugins for "
                    "enhanced analysis"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to process through plugins",
                        }
                    },
                    "required": ["email_id"],
                },
            ),
        ]
        if INTEGRATIONS_AVAILABLE
        else []
    )

    return tools


# Dedicated handler functions for each tool


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for email analysis and processing"""

    if name == "analyze_email":
        email_id = arguments.get("email_id")
        content = arguments.get("content", "")
        subject = arguments.get("subject", "")

        try:
            if email_id and email_id in storage.email_storage:
                # Analyze existing processed email
                processed_email = storage.email_storage[email_id]
                if processed_email.analysis:
                    analysis_result = {
                        "email_id": email_id,
                        "urgency_score": processed_email.analysis.urgency_score,
                        "urgency_level": processed_email.analysis.urgency_level.value,
                        "sentiment": processed_email.analysis.sentiment,
                        "confidence": processed_email.analysis.confidence,
                        "keywords": processed_email.analysis.keywords,
                        "action_items": processed_email.analysis.action_items,
                        "temporal_references": (
                            processed_email.analysis.temporal_references
                        ),
                        "tags": processed_email.analysis.tags,
                        "category": processed_email.analysis.category,
                    }
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Email {email_id} found but not yet analyzed",
                        )
                    ]
            else:
                # Analyze provided content
                if not content:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Either email_id or content must be provided",
                        )
                    ]

                # Create temporary EmailData for analysis
                from .models import EmailData

                temp_email = EmailData(
                    message_id="temp-analysis",
                    from_email="unknown@example.com",
                    to_emails=["analysis@inboxzen.com"],
                    subject=subject or "Analysis Request",
                    text_body=content,
                    html_body=None,
                    received_at=datetime.now(),
                )

                # Extract metadata
                extracted_metadata = email_extractor.extract_from_email(temp_email)
                urgency_score, analysis_urgency_level = (
                    email_extractor.calculate_urgency_score(
                        extracted_metadata.urgency_indicators
                    )
                )

                # Determine sentiment
                sentiment_indicators = extracted_metadata.sentiment_indicators
                if len(sentiment_indicators["positive"]) > len(
                    sentiment_indicators["negative"]
                ):
                    analysis_sentiment = "positive"
                elif len(sentiment_indicators["negative"]) > len(
                    sentiment_indicators["positive"]
                ):
                    analysis_sentiment = "negative"
                else:
                    analysis_sentiment = "neutral"

                analysis_result = {
                    "content_analyzed": (
                        content[:100] + "..." if len(content) > 100 else content
                    ),
                    "urgency_score": urgency_score,
                    "urgency_level": analysis_urgency_level,
                    "sentiment": analysis_sentiment,
                    "keywords": extracted_metadata.priority_keywords[:10],
                    "action_items": extracted_metadata.action_words[:5],
                    "temporal_references": extracted_metadata.temporal_references[:5],
                    "urgency_indicators": extracted_metadata.urgency_indicators,
                    "contact_info": extracted_metadata.contact_info,
                }

            return [
                TextContent(type="text", text=json.dumps(analysis_result, indent=2))
            ]

        except Exception as e:
            return [TextContent(type="text", text=f"Analysis error: {str(e)}")]

    elif name == "search_emails":
        query = str(arguments.get("query", ""))
        urgency_level: Optional[str] = arguments.get("urgency_level")
        sentiment: Optional[str] = arguments.get("sentiment")
        limit = arguments.get("limit", 10)

        try:
            results: list[Dict[str, Any]] = []
            for email in storage.email_storage.values():
                # Apply filters
                if (
                    urgency_level
                    and email.analysis
                    and email.analysis.urgency_level.value != urgency_level
                ):
                    continue
                if (
                    sentiment
                    and email.analysis
                    and email.analysis.sentiment != sentiment
                ):
                    continue

                # Apply text search
                if query:
                    searchable_text = (
                        f"{email.email_data.subject} {email.email_data.text_body or ''}"
                    )
                    if query.lower() not in searchable_text.lower():
                        continue

                # Add to results
                result: Dict[str, Any] = {
                    "id": email.id,
                    "message_id": email.email_data.message_id,
                    "from": email.email_data.from_email,
                    "subject": email.email_data.subject,
                    "received_at": email.email_data.received_at.isoformat(),
                    "status": email.status.value,
                }

                if email.analysis:
                    result.update(
                        {
                            "urgency_score": email.analysis.urgency_score,
                            "urgency_level": email.analysis.urgency_level.value,
                            "sentiment": email.analysis.sentiment,
                            "tags": email.analysis.tags,
                        }
                    )

                results.append(result)

                if len(results) >= limit:
                    break

            search_result: Dict[str, Any] = {
                "query": query,
                "filters": {"urgency_level": urgency_level, "sentiment": sentiment},
                "total_found": len(results),
                "results": results,
            }

            return [TextContent(type="text", text=json.dumps(search_result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Search error: {str(e)}")]

    elif name == "get_email_stats":
        include_distribution = arguments.get("include_distribution", True)

        try:
            total_emails = len(storage.email_storage)
            analyzed_emails = sum(
                1 for email in storage.email_storage.values() if email.analysis
            )

            stats_result: Dict[str, Any] = {
                "total_emails": total_emails,
                "total_processed": storage.stats.total_processed,
                "analyzed_emails": analyzed_emails,
                "total_errors": storage.stats.total_errors,
                "last_processed": (
                    storage.stats.last_processed.isoformat()
                    if storage.stats.last_processed
                    else None
                ),
                "avg_processing_time": (
                    sum(storage.stats.processing_times)
                    / len(storage.stats.processing_times)
                    if storage.stats.processing_times
                    else 0
                ),
            }

            if include_distribution and analyzed_emails > 0:
                urgency_distribution = {"low": 0, "medium": 0, "high": 0}
                sentiment_distribution = {"positive": 0, "negative": 0, "neutral": 0}
                urgency_scores = []

                for email in storage.email_storage.values():
                    if email.analysis:
                        urgency_distribution[email.analysis.urgency_level.value] += 1
                        sentiment_distribution[email.analysis.sentiment] += 1
                        urgency_scores.append(email.analysis.urgency_score)

                stats_result.update(
                    {
                        "urgency_distribution": urgency_distribution,
                        "sentiment_distribution": sentiment_distribution,
                        "avg_urgency_score": (
                            sum(urgency_scores) / len(urgency_scores)
                            if urgency_scores
                            else 0
                        ),
                        "max_urgency_score": (
                            max(urgency_scores) if urgency_scores else 0
                        ),
                        "min_urgency_score": (
                            min(urgency_scores) if urgency_scores else 0
                        ),
                    }
                )

            return [TextContent(type="text", text=json.dumps(stats_result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Stats error: {str(e)}")]

    elif name == "extract_tasks":
        email_id = arguments.get("email_id")
        urgency_threshold = arguments.get("urgency_threshold", 40)

        try:
            tasks: list[Dict[str, Any]] = []

            if email_id:
                # Extract tasks from specific email
                if email_id in storage.email_storage:
                    email = storage.email_storage[email_id]
                    if (
                        email.analysis
                        and email.analysis.urgency_score >= urgency_threshold
                    ):
                        task_data = {
                            "email_id": email_id,
                            "from": email.email_data.from_email,
                            "subject": email.email_data.subject,
                            "urgency_score": email.analysis.urgency_score,
                            "action_items": email.analysis.action_items,
                            "temporal_references": email.analysis.temporal_references,
                            "priority": email.analysis.urgency_level.value,
                        }
                        tasks.append(task_data)
                else:
                    return [
                        TextContent(type="text", text=f"Email {email_id} not found")
                    ]
            else:
                # Extract tasks from all emails above threshold
                for email in storage.email_storage.values():
                    if (
                        email.analysis
                        and email.analysis.urgency_score >= urgency_threshold
                    ):
                        task_data = {
                            "email_id": email.id,
                            "from": email.email_data.from_email,
                            "subject": email.email_data.subject,
                            "urgency_score": email.analysis.urgency_score,
                            "action_items": email.analysis.action_items,
                            "temporal_references": email.analysis.temporal_references,
                            "priority": email.analysis.urgency_level.value,
                        }
                        tasks.append(task_data)

                # Sort by urgency score (highest first)
                tasks.sort(key=lambda x: x["urgency_score"], reverse=True)

            result = {
                "urgency_threshold": urgency_threshold,
                "total_tasks": len(tasks),
                "tasks": tasks,
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Task extraction error: {str(e)}",
                )
            ]

    # --- Integration Tool Handlers ---
    # Integration tools (available only if integrations module is loaded)
    elif name == "export_emails" and INTEGRATIONS_AVAILABLE:
        export_format = arguments.get("format")
        limit = arguments.get("limit", 100)
        filename = arguments.get("filename")

        try:
            # Check if DataExporter is available
            if DataExporter is None:
                return [
                    TextContent(
                        type="text",
                        text="Export functionality not available - integration module not loaded",
                    )
                ]

            # Get emails to export (limited)
            emails_to_export = list(storage.email_storage.values())[:limit]

            if not emails_to_export:
                return [TextContent(type="text", text="No emails available to export")]

            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"emails_export_{timestamp}.{export_format}"

            # Export emails
            if DataExporter is None or not hasattr(DataExporter, "ExportFormat"):
                return [
                    TextContent(
                        type="text",
                        text="Export format enum not available - integration module not loaded",
                    )
                ]

            export_format_enum = DataExporter.ExportFormat(export_format)
            exported_file = DataExporter.export_emails(
                emails_to_export, export_format_enum, filename
            )

            export_result: Dict[str, Any] = {
                "success": True,
                "format": export_format,
                "exported_count": len(emails_to_export),
                "filename": exported_file,
                "exported_at": datetime.now().isoformat(),
            }

            return [TextContent(type="text", text=json.dumps(export_result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Export error: {str(e)}")]

    elif name == "list_integrations" and INTEGRATIONS_AVAILABLE:
        try:
            # Check if integration_registry is available
            if integration_registry is None:
                return [
                    TextContent(type="text", text="Integration registry not available")
                ]

            integrations_info = integration_registry.list_integrations()
            plugin_info = integration_registry.plugin_manager.get_plugin_info()

            integrations_result: Dict[str, Any] = {
                "integrations_available": True,
                "databases": integrations_info.get("databases", []),
                "ai_interfaces": integrations_info.get("ai_interfaces", []),
                "plugins": {
                    "count": len(plugin_info),
                    "registered": list(plugin_info.keys()),
                    "details": plugin_info,
                },
                "capabilities": {
                    "data_export": True,
                    "plugin_processing": True,
                    "ai_analysis": len(integrations_info.get("ai_interfaces", [])) > 0,
                    "database_storage": len(integrations_info.get("databases", [])) > 0,
                },
            }

            return [
                TextContent(type="text", text=json.dumps(integrations_result, indent=2))
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Integration listing error: {
                        str(e)}",
                )
            ]

    elif name == "process_through_plugins" and INTEGRATIONS_AVAILABLE:
        email_id = arguments.get("email_id")

        try:
            if email_id not in storage.email_storage:
                return [TextContent(type="text", text=f"Email {email_id} not found")]

            original_email = storage.email_storage[email_id]

            # Check if integration_registry is available
            if integration_registry is None:
                return [
                    TextContent(type="text", text="Integration registry not available")
                ]

            # Process through plugins
            processed_email = (
                await integration_registry.plugin_manager.process_email_through_plugins(
                    original_email
                )
            )

            # Update storage with processed email
            storage.email_storage[email_id] = processed_email

            plugin_result: Dict[str, Any] = {
                "success": True,
                "email_id": email_id,
                "plugins_applied": len(integration_registry.plugin_manager.plugins),
                "original_tags": (
                    original_email.analysis.tags if original_email.analysis else []
                ),
                "updated_tags": (
                    processed_email.analysis.tags if processed_email.analysis else []
                ),
                "processed_at": datetime.now().isoformat(),
            }

            return [TextContent(type="text", text=json.dumps(plugin_result, indent=2))]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Plugin processing error: {
                        str(e)}",
                )
            ]

    # --- Fallback for unknown tool ---
    else:
        raise ValueError(f"Unknown tool: {name}")


@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """List available prompts for email analysis"""
    return [
        Prompt(
            name="email_analysis",
            description="Prompt for comprehensive email analysis",
            arguments=[
                PromptArgument(
                    name="email_content",
                    description="The email content to analyze",
                ),
                PromptArgument(
                    name="analysis_type",
                    description="Type of analysis (urgency, sentiment, tasks)",
                ),
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict) -> PromptMessage:
    """Get prompt for email analysis"""
    if name == "email_analysis":
        email_content = arguments.get("email_content", "")
        analysis_type = arguments.get("analysis_type", "comprehensive")

        prompt_text = f"""Analyze the following email for {analysis_type} analysis:

Email Content:
{email_content}

Please provide:
1. Urgency score (0-100)
2. Sentiment analysis
3. Key action items
4. Suggested tags
5. Priority level
"""
        return PromptMessage(
            role="user", content=TextContent(type="text", text=prompt_text)
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


async def main():
    """Main entry point for MCP server over stdio"""

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    # Start the MCP server over stdio
    asyncio.run(main())
