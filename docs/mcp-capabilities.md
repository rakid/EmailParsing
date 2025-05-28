# MCP Server Capabilities Documentation

## Inbox Zen Email Parsing MCP Server

**Protocol Version:** Model Context Protocol 1.0  
**Server Implementation:** Python MCP SDK  
**Capabilities:** Resources, Tools

---

## Server Information

```json
{
  "name": "inbox-zen-email-parser",
  "version": "1.0.0",
  "protocol_version": "2024-11-05",
  "capabilities": {
    "resources": {
      "subscribe": false,
      "list_changed": false
    },
    "tools": {
      "list_changed": false
    }
  },
  "instructions": "Email parsing and analysis server for Inbox Zen. Provides access to processed emails, analytics, and intelligent analysis tools."
}
```

---

## MCP Resources

### Available Resources

The server exposes the following MCP resources for client access:

#### 1. `email://processed`

**Description:** Access to all processed emails with full metadata  
**Content Type:** `application/json`  
**Features:**

- Full email content and headers
- Extracted metadata (urgency, sentiment, keywords)
- Task extraction results
- Timestamps and processing information

**Example URI:** `email://processed`

#### 2. `email://stats`

**Description:** System statistics and metrics  
**Content Type:** `application/json`  
**Features:**

- Total email count
- Processing performance metrics
- System health indicators
- Memory and uptime statistics

**Example URI:** `email://stats`

#### 3. `email://recent`

**Description:** Recently processed emails (last 24 hours)  
**Content Type:** `application/json`  
**Features:**

- Time-filtered email list
- Optimized for quick access
- Includes full metadata
- Sorted by processing time

**Example URI:** `email://recent`

#### 4. `email://analytics`

**Description:** Comprehensive analytics and distributions  
**Content Type:** `application/json`  
**Features:**

- Urgency and sentiment distributions
- Time-series analysis
- Keyword frequency analysis
- Performance trends

**Example URI:** `email://analytics`

#### 5. `email://high-urgency`

**Description:** High-urgency emails only (filtered view)  
**Content Type:** `application/json`  
**Features:**

- Pre-filtered for urgency > 70
- Priority email identification
- Includes all metadata
- Sorted by urgency score

**Example URI:** `email://high-urgency`

#### 6. `email://tasks`

**Description:** Extracted tasks from all emails  
**Content Type:** `application/json`  
**Features:**

- Task extraction results
- Urgency scoring for tasks
- Deadline detection
- Source email references

**Example URI:** `email://tasks`

---

## MCP Tools

### Available Tools

The server provides the following tools for interactive email analysis:

#### 1. `analyze_email`

**Description:** Perform detailed analysis on a specific email  
**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "email_id": {
      "type": "string",
      "description": "Unique identifier of the email to analyze"
    }
  },
  "required": ["email_id"]
}
```

**Output:** Complete analysis including urgency, sentiment, keywords, entities, and tasks

#### 2. `search_emails`

**Description:** Search emails with advanced filtering options  
**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query for email content"
    },
    "urgency_filter": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "description": "Filter by urgency level"
    },
    "sentiment_filter": {
      "type": "string",
      "enum": ["positive", "negative", "neutral"],
      "description": "Filter by sentiment"
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 10,
      "description": "Maximum number of results"
    }
  },
  "required": ["query"]
}
```

**Output:** Matching emails with relevance scoring

#### 3. `get_email_stats`

**Description:** Get comprehensive statistics about processed emails  
**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "timeframe": {
      "type": "string",
      "enum": ["hour", "day", "week", "month", "all"],
      "default": "day",
      "description": "Time period for statistics"
    }
  }
}
```

**Output:** Statistical analysis and distributions

#### 4. `extract_tasks`

**Description:** Extract actionable tasks from emails with urgency scoring  
**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "urgency_threshold": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "default": 50,
      "description": "Minimum urgency score for task inclusion"
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 20,
      "description": "Maximum number of tasks to return"
    }
  }
}
```

**Output:** List of extracted tasks with urgency scores and source emails

---

## Authentication & Security

### Current Implementation

- **Authentication:** None (development mode)
- **Authorization:** Open access to all resources and tools
- **Input Validation:** Comprehensive parameter validation
- **Rate Limiting:** None (planned for production)

### Production Considerations

- Implement API key authentication
- Add role-based access control
- Enable rate limiting and throttling
- Add audit logging for sensitive operations

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
      "parameter": "Additional context if applicable"
    }
  }
}
```

### Common Error Codes

- `INVALID_EMAIL_ID`: Email not found or invalid ID format
- `INVALID_PARAMETERS`: Missing or invalid tool parameters
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `PROCESSING_ERROR`: Error during email analysis or processing

---

## Performance Characteristics

### Response Times

- **Resource Access:** < 100ms for cached resources
- **Tool Execution:** < 2s for complex analysis operations
- **Search Operations:** < 500ms for typical queries

### Scalability

- **Concurrent Requests:** Supports multiple simultaneous MCP clients
- **Memory Usage:** Optimized for in-memory storage with configurable limits
- **Processing Capacity:** Designed for real-time email processing

---

## Integration Examples

### Basic Resource Access

```python
# Using MCP client to access processed emails
resource = await client.read_resource("email://processed")
emails = json.loads(resource.contents[0].text)
```

### Tool Usage

```python
# Analyze a specific email
result = await client.call_tool("analyze_email", {"email_id": "email_123"})
analysis = json.loads(result.content[0].text)
```

### Search and Filter

```python
# Search for urgent emails
results = await client.call_tool("search_emails", {
    "query": "meeting",
    "urgency_filter": "high",
    "limit": 5
})
```

---

## Development and Testing

### Local Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Start MCP server: `python -m src.server`
3. Server runs on stdio transport by default
4. REST API available on `http://localhost:8000` for debugging

### Testing Tools

- Use `test_mcp_tools.py` for tool validation
- Use `test_api_layer.py` for resource testing
- REST API available for manual testing and debugging

---

## Future Enhancements

### Planned Features

- Real-time email notifications via MCP subscriptions
- Advanced AI analysis integration
- Database persistence options
- Multi-tenant support
- Enhanced security features

### Extension Points

- Custom analysis patterns
- Additional data sources
- Enhanced entity extraction
- Integration with external AI services
