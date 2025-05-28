# MCP Client Configuration Examples

This document provides configuration examples for integrating with the Inbox Zen Email Parsing MCP Server across different client environments.

---

## General Configuration

### Server Connection Details

- **Server Name:** `inbox-zen-email-parser`
- **Protocol:** Model Context Protocol (MCP) 1.0
- **Transport:** stdio (default) or HTTP
- **Base URL (REST):** `http://localhost:8000` (development)

---

## Claude Desktop Configuration

### Basic Configuration

Add to your Claude Desktop configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "inbox-zen-email-parser": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/EmailParsing",
      "env": {
        "PYTHONPATH": "/path/to/EmailParsing"
      }
    }
  }
}
```

### Advanced Configuration with Environment Variables

```json
{
  "mcpServers": {
    "inbox-zen-email-parser": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/EmailParsing",
      "env": {
        "PYTHONPATH": "/path/to/EmailParsing",
        "LOG_LEVEL": "INFO",
        "EMAIL_STORAGE_LIMIT": "1000",
        "ENABLE_DEBUG_MODE": "true"
      }
    }
  }
}
```

---

## Python MCP Client Configuration

### Basic Client Setup

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def connect_to_email_server():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.server"],
        cwd="/path/to/EmailParsing",
        env={"PYTHONPATH": "/path/to/EmailParsing"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List available resources
            resources = await session.list_resources()
            print("Available resources:", [r.name for r in resources.resources])

            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            return session

# Usage
if __name__ == "__main__":
    asyncio.run(connect_to_email_server())
```

### Advanced Client with Error Handling

```python
import asyncio
import json
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailMCPClient:
    def __init__(self, server_path="/path/to/EmailParsing"):
        self.server_params = StdioServerParameters(
            command="python",
            args=["-m", "src.server"],
            cwd=server_path,
            env={"PYTHONPATH": server_path}
        )
        self.session = None

    async def connect(self):
        """Establish connection to MCP server"""
        try:
            self.client_context = stdio_client(self.server_params)
            self.read, self.write = await self.client_context.__aenter__()

            self.session_context = ClientSession(self.read, self.write)
            self.session = await self.session_context.__aenter__()

            await self.session.initialize()
            logger.info("Successfully connected to email MCP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def disconnect(self):
        """Clean up connection"""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.client_context:
            await self.client_context.__aexit__(None, None, None)

    async def get_recent_emails(self):
        """Get recent emails from the server"""
        try:
            resource = await self.session.read_resource("email://recent")
            return json.loads(resource.contents[0].text)
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            return None

    async def analyze_email(self, email_id):
        """Analyze a specific email"""
        try:
            result = await self.session.call_tool("analyze_email", {"email_id": email_id})
            return json.loads(result.content[0].text)
        except Exception as e:
            logger.error(f"Failed to analyze email {email_id}: {e}")
            return None

    async def search_emails(self, query, urgency_filter=None, limit=10):
        """Search emails with optional filtering"""
        try:
            params = {"query": query, "limit": limit}
            if urgency_filter:
                params["urgency_filter"] = urgency_filter

            result = await self.session.call_tool("search_emails", params)
            return json.loads(result.content[0].text)
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return None

# Usage example
async def main():
    client = EmailMCPClient()

    if await client.connect():
        # Get recent emails
        recent = await client.get_recent_emails()
        print(f"Found {len(recent.get('emails', []))} recent emails")

        # Search for urgent emails
        urgent = await client.search_emails("meeting", urgency_filter="high")
        print(f"Found {len(urgent.get('results', []))} urgent meeting emails")

        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Node.js MCP Client Configuration

### Basic Setup

```javascript
// package.json dependencies
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0"
  }
}
```

```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { spawn } from "child_process";

class EmailMCPClient {
  constructor(serverPath = "/path/to/EmailParsing") {
    this.serverPath = serverPath;
    this.client = null;
  }

  async connect() {
    try {
      // Spawn the Python MCP server
      const serverProcess = spawn("python", ["-m", "src.server"], {
        cwd: this.serverPath,
        env: { ...process.env, PYTHONPATH: this.serverPath },
      });

      // Create transport and client
      const transport = new StdioClientTransport({
        reader: serverProcess.stdout,
        writer: serverProcess.stdin,
      });

      this.client = new Client(
        { name: "email-client", version: "1.0.0" },
        { capabilities: {} },
      );

      await this.client.connect(transport);
      console.log("Connected to email MCP server");
      return true;
    } catch (error) {
      console.error("Failed to connect:", error);
      return false;
    }
  }

  async getRecentEmails() {
    try {
      const resource = await this.client.readResource({
        uri: "email://recent",
      });
      return JSON.parse(resource.contents[0].text);
    } catch (error) {
      console.error("Failed to get recent emails:", error);
      return null;
    }
  }

  async analyzeEmail(emailId) {
    try {
      const result = await this.client.callTool({
        name: "analyze_email",
        arguments: { email_id: emailId },
      });
      return JSON.parse(result.content[0].text);
    } catch (error) {
      console.error("Failed to analyze email:", error);
      return null;
    }
  }
}

// Usage
const client = new EmailMCPClient();
await client.connect();
const emails = await client.getRecentEmails();
console.log(`Found ${emails.emails.length} recent emails`);
```

---

## Configuration for Different Environments

### Development Environment

```bash
# Environment variables for development
export LOG_LEVEL=DEBUG
export ENABLE_DEBUG_MODE=true
export EMAIL_STORAGE_LIMIT=100
export REST_API_PORT=8000
```

### Production Environment

```bash
# Environment variables for production
export LOG_LEVEL=INFO
export ENABLE_DEBUG_MODE=false
export EMAIL_STORAGE_LIMIT=10000
export REST_API_PORT=8080
export ENABLE_AUTHENTICATION=true
export API_KEY_REQUIRED=true
```

### Docker Configuration

```dockerfile
# Dockerfile for containerized deployment
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY docs/ ./docs/

EXPOSE 8080
ENV LOG_LEVEL=INFO
ENV REST_API_PORT=8080

CMD ["python", "-m", "src.server"]
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  email-mcp-server:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LOG_LEVEL=INFO
      - EMAIL_STORAGE_LIMIT=10000
      - ENABLE_DEBUG_MODE=false
    volumes:
      - ./logs:/app/logs
```

---

## Integration Patterns

### Pattern 1: Real-time Email Monitoring

```python
async def monitor_emails():
    client = EmailMCPClient()
    await client.connect()

    while True:
        recent = await client.get_recent_emails()
        new_emails = [e for e in recent['emails']
                     if e['metadata']['urgency_level'] == 'high']

        for email in new_emails:
            analysis = await client.analyze_email(email['id'])
            # Process high-urgency emails immediately
            await handle_urgent_email(email, analysis)

        await asyncio.sleep(30)  # Check every 30 seconds
```

### Pattern 2: Batch Email Analysis

```python
async def analyze_all_unprocessed():
    client = EmailMCPClient()
    await client.connect()

    # Get all emails
    all_emails = await client.session.read_resource("email://processed")
    emails_data = json.loads(all_emails.contents[0].text)

    for email in emails_data['emails']:
        if not email.get('analyzed', False):
            analysis = await client.analyze_email(email['id'])
            # Store analysis results
            await store_analysis(email['id'], analysis)
```

### Pattern 3: Dashboard Integration

```python
async def get_dashboard_data():
    client = EmailMCPClient()
    await client.connect()

    # Get analytics for dashboard
    analytics = await client.session.read_resource("email://analytics")
    stats = await client.session.call_tool("get_email_stats", {"timeframe": "day"})
    high_urgency = await client.session.read_resource("email://high-urgency")

    return {
        'analytics': json.loads(analytics.contents[0].text),
        'stats': json.loads(stats.content[0].text),
        'urgent_emails': json.loads(high_urgency.contents[0].text)
    }
```

---

## Troubleshooting

### Common Issues

1. **Connection Failed**

   - Verify Python path and working directory
   - Check that all dependencies are installed
   - Ensure server script is executable

2. **Resource Not Found**

   - Verify resource URI format (e.g., `email://processed`)
   - Check server logs for errors
   - Ensure server has processed some emails

3. **Tool Call Timeout**
   - Increase timeout settings in client configuration
   - Check server performance and resource usage
   - Verify tool parameters are valid

### Debug Mode

Enable debug mode for verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Set environment variable
os.environ['ENABLE_DEBUG_MODE'] = 'true'
```

### Health Check

Always verify server health before operations:

```python
async def health_check():
    try:
        # Try a simple resource access
        stats = await client.session.read_resource("email://stats")
        return True
    except Exception:
        return False
```
