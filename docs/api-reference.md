# 📖 Inbox Zen MCP Server API Reference

Complete API reference for the Inbox Zen Email Parsing MCP Server, covering MCP resources, tools, REST endpoints, and data formats.

---

## 🔌 MCP Protocol Interface

### Server Information

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
  }
}
```

---

## 📄 MCP Resources

### 1. Processed Emails Resource

**URI:** `email://processed`  
**Content Type:** `application/json`  
**Description:** Access to all processed emails with full analysis

#### Response Format

```json
{
  "emails": [
    {
      "id": "email_123456789",
      "timestamp": "2025-05-28T10:30:00Z",
      "data": {
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "subject": "Important Project Update",
        "text_body": "Email content here...",
        "html_body": "<html>Email content here...</html>",
        "headers": {
          "message-id": "<abc123@example.com>",
          "date": "Tue, 28 May 2025 10:30:00 +0000"
        },
        "attachments": [
          {
            "name": "document.pdf",
            "content_type": "application/pdf",
            "size": 245760
          }
        ]
      },
      "analysis": {
        "urgency_level": "high",
        "urgency_score": 0.85,
        "sentiment": "neutral",
        "sentiment_score": 0.02,
        "extracted_tasks": [
          {
            "task": "Review the quarterly report",
            "confidence": 0.92
          }
        ],
        "keywords": ["project", "deadline", "review", "urgent"],
        "language": "en",
        "processing_time": 0.008
      }
    }
  ],
  "total_count": 1,
  "metadata": {
    "retrieved_at": "2025-05-28T10:35:00Z",
    "server_version": "1.0.0"
  }
}
```

### 2. Email Statistics Resource

**URI:** `email://stats`  
**Content Type:** `application/json`  
**Description:** Real-time processing statistics and analytics

#### Response Format

```json
{
  "stats": {
    "total_processed": 156,
    "total_urgent": 23,
    "total_tasks_found": 45,
    "average_processing_time": 0.007,
    "languages_detected": {
      "en": 120,
      "fr": 25,
      "es": 8,
      "de": 3
    },
    "urgency_distribution": {
      "high": 23,
      "medium": 67,
      "low": 66
    },
    "sentiment_distribution": {
      "positive": 89,
      "neutral": 54,
      "negative": 13
    },
    "hourly_volume": {
      "00": 2,
      "01": 1,
      "09": 15,
      "10": 23,
      "14": 18
    }
  },
  "metadata": {
    "last_updated": "2025-05-28T10:35:00Z",
    "server_uptime": 3600,
    "storage_usage": {
      "emails_stored": 156,
      "storage_limit": 1000,
      "usage_percentage": 15.6
    }
  }
}
```

---

## 🛠️ MCP Tools

### 1. Get Processed Emails

**Name:** `get_processed_emails`  
**Description:** Retrieve processed emails with optional filtering

#### Parameters

```json
{
  "limit": {
    "type": "number",
    "description": "Maximum number of emails to return (default: 50, max: 100)",
    "default": 50
  },
  "offset": {
    "type": "number", 
    "description": "Number of emails to skip for pagination (default: 0)",
    "default": 0
  },
  "urgency_filter": {
    "type": "string",
    "description": "Filter by urgency level: 'high', 'medium', 'low'",
    "enum": ["high", "medium", "low"],
    "required": false
  },
  "date_from": {
    "type": "string",
    "description": "ISO 8601 date string for start date filter",
    "format": "date-time",
    "required": false
  },
  "date_to": {
    "type": "string", 
    "description": "ISO 8601 date string for end date filter",
    "format": "date-time",
    "required": false
  }
}
```

#### Example Usage

```json
{
  "name": "get_processed_emails",
  "arguments": {
    "limit": 10,
    "urgency_filter": "high",
    "date_from": "2025-05-28T00:00:00Z"
  }
}
```

#### Response

```json
{
  "emails": [...],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 23,
    "has_more": true
  }
}
```

### 2. Get Email Statistics

**Name:** `get_email_stats`  
**Description:** Retrieve comprehensive email processing statistics

#### Parameters

```json
{
  "period": {
    "type": "string",
    "description": "Statistics period: 'hour', 'day', 'week', 'month', 'all'",
    "enum": ["hour", "day", "week", "month", "all"],
    "default": "day"
  },
  "include_detailed": {
    "type": "boolean",
    "description": "Include detailed breakdown by categories",
    "default": false
  }
}
```

#### Example Usage

```json
{
  "name": "get_email_stats", 
  "arguments": {
    "period": "day",
    "include_detailed": true
  }
}
```

### 3. Search Emails

**Name:** `search_emails`  
**Description:** Search through processed emails with various criteria

#### Parameters

```json
{
  "query": {
    "type": "string",
    "description": "Search query string (searches subject, body, and keywords)",
    "required": true
  },
  "search_type": {
    "type": "string",
    "description": "Type of search: 'full_text', 'keywords', 'subject_only'",
    "enum": ["full_text", "keywords", "subject_only"],
    "default": "full_text"
  },
  "limit": {
    "type": "number",
    "description": "Maximum number of results (default: 20, max: 50)",
    "default": 20
  }
}
```

#### Example Usage

```json
{
  "name": "search_emails",
  "arguments": {
    "query": "project deadline urgent",
    "search_type": "keywords",
    "limit": 10
  }
}
```

### 4. Export Emails (Integration Tool)

**Name:** `export_emails`  
**Description:** Export processed emails in various formats

#### Parameters

```json
{
  "format": {
    "type": "string",
    "description": "Export format",
    "enum": ["json", "csv", "jsonl", "parquet"],
    "required": true
  },
  "filter_criteria": {
    "type": "object",
    "description": "Filtering criteria for export",
    "properties": {
      "urgency_level": {"type": "string"},
      "date_range": {
        "type": "object",
        "properties": {
          "start": {"type": "string"},
          "end": {"type": "string"}
        }
      },
      "include_analysis": {"type": "boolean", "default": true}
    },
    "required": false
  }
}
```

### 5. List Integrations

**Name:** `list_integrations`  
**Description:** List available integration plugins and capabilities

#### Parameters

```json
{
  "include_details": {
    "type": "boolean",
    "description": "Include detailed plugin information",
    "default": false
  }
}
```

### 6. Process Through Plugins

**Name:** `process_through_plugins`  
**Description:** Process emails through specific integration plugins

#### Parameters

```json
{
  "plugin_names": {
    "type": "array",
    "description": "List of plugin names to use for processing",
    "items": {"type": "string"},
    "required": true
  },
  "email_filters": {
    "type": "object",
    "description": "Filters for selecting emails to process",
    "required": false
  }
}
```

---

## 🌐 REST API Endpoints

### Webhook Endpoint

**POST** `/webhook`  
**Content-Type:** `application/json`  
**Authentication:** HMAC signature validation

#### Headers

```
Content-Type: application/json
X-Postmark-Signature: sha256=<signature>
```

#### Request Body (Postmark Format)

```json
{
  "FromName": "John Doe",
  "MessageStream": "inbound",
  "From": "john@example.com",
  "FromFull": {
    "Email": "john@example.com",
    "Name": "John Doe"
  },
  "To": "inbox@yourapp.com",
  "ToFull": [
    {
      "Email": "inbox@yourapp.com", 
      "Name": "Your App"
    }
  ],
  "Cc": "",
  "CcFull": [],
  "Bcc": "",
  "BccFull": [],
  "OriginalRecipient": "inbox@yourapp.com",
  "Subject": "Important Project Update",
  "MessageID": "abc123def456",
  "ReplyTo": "john@example.com",
  "MailboxHash": "hash123",
  "Date": "Tue, 28 May 2025 10:30:00 +0000",
  "TextBody": "Email text content here...",
  "HtmlBody": "<html>Email HTML content here...</html>",
  "StrippedTextReply": "",
  "Tag": "",
  "Headers": [
    {
      "Name": "Message-ID",
      "Value": "<abc123@example.com>"
    }
  ],
  "Attachments": [
    {
      "Name": "document.pdf",
      "Content": "base64-encoded-content",
      "ContentType": "application/pdf",
      "ContentLength": 245760
    }
  ]
}
```

#### Response

```json
{
  "status": "success",
  "message": "Email processed successfully",
  "email_id": "email_123456789",
  "processing_time": 0.008,
  "analysis": {
    "urgency_level": "high",
    "sentiment": "neutral",
    "tasks_found": 1,
    "keywords": ["project", "deadline", "review"]
  }
}
```

### Health Check Endpoints

**GET** `/health`  
**Description:** Server health status

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "last_email_processed": "2025-05-28T10:30:00Z",
  "storage": {
    "emails_stored": 156,
    "storage_usage": "15.6%"
  }
}
```

**GET** `/metrics`  
**Description:** Prometheus-compatible metrics (if enabled)

---

## 📊 Data Models

### ProcessedEmail Model

```typescript
interface ProcessedEmail {
  id: string;                    // Unique email identifier
  timestamp: string;             // ISO 8601 timestamp
  data: EmailData;              // Original email data
  analysis: EmailAnalysis;      // Analysis results
}
```

### EmailData Model

```typescript
interface EmailData {
  from: string;                 // Sender email
  to: string[];                // Recipients
  cc?: string[];               // CC recipients
  bcc?: string[];              // BCC recipients
  subject: string;             // Email subject
  text_body: string;           // Plain text content
  html_body?: string;          // HTML content
  headers: Record<string, string>; // Email headers
  attachments?: Attachment[];   // File attachments
  message_id: string;          // Unique message ID
  date: string;                // Email date
}
```

### EmailAnalysis Model

```typescript
interface EmailAnalysis {
  urgency_level: "high" | "medium" | "low";
  urgency_score: number;        // 0.0 - 1.0
  sentiment: "positive" | "neutral" | "negative";
  sentiment_score: number;      // -1.0 to 1.0
  extracted_tasks: Task[];      // Extracted action items
  keywords: string[];           // Key terms found
  language: string;             // Detected language (ISO 639-1)
  processing_time: number;      // Processing time in seconds
  metadata?: Record<string, any>; // Additional analysis data
}
```

### Task Model

```typescript
interface Task {
  task: string;                // Task description
  confidence: number;          // Confidence score 0.0-1.0
  due_date?: string;          // Extracted due date
  priority?: "high" | "medium" | "low";
  assigned_to?: string;       // Extracted assignee
}
```

### EmailStats Model

```typescript
interface EmailStats {
  total_processed: number;
  total_urgent: number;
  total_tasks_found: number;
  average_processing_time: number;
  languages_detected: Record<string, number>;
  urgency_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
  hourly_volume: Record<string, number>;
}
```

---

## 🔌 Integration Formats

### AIAnalysisFormat

```typescript
interface AIAnalysisFormat {
  email_id: string;
  content: {
    subject: string;
    body: string;
    metadata: Record<string, any>;
  };
  analysis_request: {
    urgency_analysis: boolean;
    sentiment_analysis: boolean;
    task_extraction: boolean;
    keyword_extraction: boolean;
  };
  context: {
    processing_timestamp: string;
    server_version: string;
  };
}
```

### DatabaseFormat

```typescript
interface DatabaseFormat {
  email_id: string;
  sender: string;
  recipients: string[];
  subject: string;
  content_text: string;
  content_html?: string;
  urgency_level: string;
  urgency_score: number;
  sentiment: string;
  sentiment_score: number;
  keywords: string[];
  tasks: string[];
  language: string;
  processed_at: string;
  processing_time: number;
}
```

---

## 🚨 Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "data.from",
      "value": "invalid-email",
      "expected": "valid email address"
    },
    "timestamp": "2025-05-28T10:35:00Z",
    "request_id": "req_123456"
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `AUTHENTICATION_ERROR` - Invalid or missing authentication
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `PROCESSING_ERROR` - Email processing failed
- `STORAGE_ERROR` - Storage operation failed
- `INTEGRATION_ERROR` - Plugin or integration failure
- `INTERNAL_ERROR` - Unexpected server error

---

## 📝 Usage Examples

### MCP Client Integration

```python
import asyncio
from mcp import Client

async def get_urgent_emails():
    client = Client()
    await client.connect("stdio", ["python", "-m", "src.server"])
    
    # Get urgent emails
    result = await client.call_tool(
        "get_processed_emails",
        {"urgency_filter": "high", "limit": 10}
    )
    
    return result.content

# Get email statistics
async def get_daily_stats():
    client = Client()
    await client.connect("stdio", ["python", "-m", "src.server"])
    
    stats = await client.call_tool(
        "get_email_stats",
        {"period": "day", "include_detailed": True}
    )
    
    return stats.content
```

### REST API Usage

```python
import requests

# Send webhook (simulated)
def send_test_webhook():
    webhook_data = {
        "From": "test@example.com",
        "To": "inbox@yourapp.com", 
        "Subject": "Test Email",
        "TextBody": "This is a test email with urgent deadline.",
        "MessageID": "test123"
    }
    
    response = requests.post(
        "http://localhost:8001/webhook",
        json=webhook_data,
        headers={"X-Postmark-Signature": "sha256=test_signature"}
    )
    
    return response.json()

# Check server health
def check_health():
    response = requests.get("http://localhost:8000/health")
    return response.json()
```

---

## 🔧 Advanced Configuration

### Custom Analysis Patterns

```python
# Add custom urgency patterns
CUSTOM_URGENCY_PATTERNS = [
    r"emergency",
    r"asap",
    r"deadline.*tomorrow",
    r"critical.*issue"
]

# Add custom task extraction patterns  
CUSTOM_TASK_PATTERNS = [
    r"please (review|check|verify|confirm) (.+)",
    r"need to (complete|finish|submit) (.+)",
    r"action required: (.+)"
]
```

### Plugin Development

```python
from src.integrations import PluginInterface

class CustomAnalysisPlugin(PluginInterface):
    def get_name(self) -> str:
        return "custom_analysis"
    
    def get_version(self) -> str:
        return "1.0.0"
        
    def process_email(self, email_data: dict) -> dict:
        # Custom processing logic
        return {
            "custom_score": 0.85,
            "custom_tags": ["important", "business"]
        }
```

This API reference provides complete coverage of all interfaces and data formats available in the Inbox Zen MCP Server. For setup instructions, see the [Setup Guide](setup-guide.md), and for integration examples, see [Client Examples](client-examples.md).
