"""
MCP Server API endpoint for Vercel deployment
Provides HTTP access to MCP server functionality
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

# Add the project root and src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import MCP server and related components
try:
    from src import server as mcp_server
    from src import storage
    from src.models import EmailData, ProcessedEmail, EmailAnalysis
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: MCP server import failed: {e}")
    MCP_AVAILABLE = False

app = FastAPI(
    title="Inbox Zen MCP Server API",
    description="HTTP API wrapper for MCP Server functionality",
    version="1.0.0"
)

# Request/Response models
class MCPResourceRequest(BaseModel):
    uri: str

class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPPromptRequest(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None

@app.get("/mcp/health")
async def mcp_health():
    """Health check for MCP server"""
    return {
        "status": "healthy" if MCP_AVAILABLE else "degraded",
        "mcp_available": MCP_AVAILABLE,
        "timestamp": "2025-01-28T10:00:00Z"
    }

@app.get("/mcp/resources")
async def list_resources():
    """List available MCP resources"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        resources = await mcp_server.handle_list_resources()
        return {
            "resources": [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType
                }
                for resource in resources
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list resources: {str(e)}")

@app.post("/mcp/resources/read")
async def read_resource(request: MCPResourceRequest):
    """Read MCP resource content"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        content = await mcp_server.handle_read_resource(request.uri)
        return {
            "uri": request.uri,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resource: {str(e)}")

@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        tools = await mcp_server.handle_list_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@app.post("/mcp/tools/call")
async def call_tool(request: MCPToolRequest):
    """Call MCP tool"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        result = await mcp_server.handle_call_tool(request.name, request.arguments)
        return {
            "tool": request.name,
            "arguments": request.arguments,
            "result": [
                {
                    "type": content.type,
                    "text": content.text
                }
                for content in result
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call tool: {str(e)}")

@app.get("/mcp/prompts")
async def list_prompts():
    """List available MCP prompts"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        prompts = await mcp_server.handle_list_prompts()
        return {
            "prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments
                }
                for prompt in prompts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")

@app.post("/mcp/prompts/get")
async def get_prompt(request: MCPPromptRequest):
    """Get MCP prompt"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        result = await mcp_server.handle_get_prompt(request.name, request.arguments)
        return {
            "prompt": request.name,
            "arguments": request.arguments,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt: {str(e)}")

# Additional endpoints for email data access
@app.get("/mcp/emails/stats")
async def get_email_stats():
    """Get email processing statistics via MCP"""
    if not MCP_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "MCP server not available", "fallback_stats": storage.stats.dict()}
        )
    
    try:
        result = await mcp_server.handle_call_tool("get_email_stats", {})
        if result:
            return json.loads(result[0].text)
        return {"error": "No stats available"}
    except Exception as e:
        # Fallback to direct storage access
        return {
            "total_processed": storage.stats.total_processed,
            "total_errors": storage.stats.total_errors,
            "avg_urgency_score": storage.stats.avg_urgency_score,
            "fallback": True,
            "error": str(e)
        }

@app.get("/mcp/emails/recent")
async def get_recent_emails(limit: int = 10):
    """Get recent emails via MCP"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="MCP server not available")
    
    try:
        result = await mcp_server.handle_call_tool("get_processed_emails", {"limit": limit})
        if result:
            return json.loads(result[0].text)
        return {"emails": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent emails: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "available_endpoints": [
                "/mcp/health",
                "/mcp/resources",
                "/mcp/resources/read",
                "/mcp/tools",
                "/mcp/tools/call",
                "/mcp/prompts",
                "/mcp/prompts/get",
                "/mcp/emails/stats",
                "/mcp/emails/recent"
            ]
        }
    )

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
