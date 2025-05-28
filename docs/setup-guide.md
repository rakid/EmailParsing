# 🚀 Inbox Zen MCP Server Setup Guide

This comprehensive guide covers installation, configuration, and deployment of the Inbox Zen Email Parsing MCP Server for both development and production environments.

---

## 📋 Prerequisites

### System Requirements

- **Python:** 3.12+ (recommended: 3.12.x)
- **Operating System:** Linux, macOS, or Windows WSL2
- **Memory:** Minimum 512MB RAM (recommended: 1GB+)
- **Storage:** 100MB+ for application, additional space for email storage
- **Network:** Internet access for webhook endpoints (production)

### External Services

- **Postmark Account:** For email webhook integration
- **Optional:** Docker for containerized deployment

---

## 🔧 Installation

### Option 1: Standard Python Installation

```bash
# Clone the repository
git clone <repository-url>
cd EmailParsing

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m src.server --help
```

### Option 2: Poetry Installation (Recommended for Development)

```bash
# Clone the repository
git clone <repository-url>
cd EmailParsing

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Verify installation
python -m src.server --help
```

### Option 3: Docker Installation

```bash
# Clone the repository
git clone <repository-url>
cd EmailParsing

# Build Docker image
docker build -t inbox-zen-mcp .

# Run container
docker run -p 8000:8000 -p 8001:8001 \
  -e POSTMARK_WEBHOOK_SECRET=your_secret \
  inbox-zen-mcp
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Postmark Configuration
POSTMARK_WEBHOOK_SECRET=your_postmark_webhook_secret_here

# Server Configuration (optional)
MCP_SERVER_NAME=inbox-zen-email-parser
MCP_SERVER_VERSION=1.0.0
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
WEBHOOK_PORT=8001

# Processing Configuration (optional)
MAX_EMAIL_SIZE=10485760  # 10MB
PROCESSING_TIMEOUT=30
ENABLE_REAL_TIME_LOGGING=true

# Storage Configuration (optional)
EMAIL_STORAGE_LIMIT=1000
CLEANUP_INTERVAL_HOURS=24

# Logging Configuration (optional)
LOG_LEVEL=INFO
LOG_FILE=logs/inbox-zen.log
ERROR_LOG_FILE=logs/errors.log
```

### Configuration File (config/config.yaml)

```yaml
# Server configuration
server:
  name: "inbox-zen-email-parser"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000
  debug: false

# Webhook configuration
webhook:
  port: 8001
  host: "0.0.0.0"
  endpoint: "/webhook"

# Postmark integration
postmark:
  webhook_secret: "${POSTMARK_WEBHOOK_SECRET}"
  signature_header: "X-Postmark-Signature"
  validate_signatures: true

# Email processing
processing:
  max_email_size: 10485760  # 10MB
  timeout_seconds: 30
  enable_real_time_logging: true
  batch_size: 50

# Storage configuration
storage:
  max_emails: 1000
  cleanup_interval_hours: 24
  backup_enabled: false

# Analysis configuration
analysis:
  enable_urgency_detection: true
  enable_sentiment_analysis: true
  enable_task_extraction: true
  enable_keyword_extraction: true
  languages: ["en", "fr", "es", "de"]

# Integration settings
integrations:
  enable_plugins: true
  enable_database_export: true
  enable_ai_analysis: true
  export_formats: ["json", "csv", "jsonl", "parquet"]

# Logging configuration
logging:
  level: "INFO"
  file: "logs/inbox-zen.log"
  error_file: "logs/errors.log"
  max_file_size: "10MB"
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## 🚀 Quick Start

### 1. Basic Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Postmark webhook secret

# 3. Start the MCP server
python -m src.server

# 4. In another terminal, start the webhook server
python -m src.webhook
```

### 2. Verify Installation

```bash
# Test MCP server connectivity
python -c "from src.server import server; print('MCP Server: OK')"

# Test webhook server
curl -X POST http://localhost:8001/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "ping"}'
```

### 3. Configure Postmark Webhook

1. Log into your Postmark account
2. Navigate to Server Settings → Webhooks
3. Add a new webhook:
   - **URL:** `https://your-domain.com/webhook` (or `http://localhost:8001/webhook` for testing)
   - **Events:** Select "Inbound" events
   - **Secret:** Use the same secret from your `.env` file

---

## 🔌 MCP Client Integration

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "inbox-zen-email-parser": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/EmailParsing",
      "env": {
        "PYTHONPATH": "/path/to/EmailParsing",
        "POSTMARK_WEBHOOK_SECRET": "your_secret_here"
      }
    }
  }
}
```

### Custom MCP Client

```python
from mcp import Client
import asyncio

async def connect_to_inbox_zen():
    client = Client()
    
    # Connect to server
    await client.connect("stdio", ["python", "-m", "src.server"])
    
    # List available resources
    resources = await client.list_resources()
    print("Available resources:", [r.name for r in resources])
    
    # List available tools
    tools = await client.list_tools()
    print("Available tools:", [t.name for t in tools])
    
    return client

# Usage
client = asyncio.run(connect_to_inbox_zen())
```

---

## 🐳 Docker Deployment

### Development Environment

```bash
# Build and run with Docker Compose (if available)
docker-compose up -d

# Or manually with Docker
docker build -t inbox-zen-mcp .
docker run -d \
  --name inbox-zen \
  -p 8000:8000 \
  -p 8001:8001 \
  -e POSTMARK_WEBHOOK_SECRET=your_secret \
  -v $(pwd)/logs:/app/logs \
  inbox-zen-mcp
```

### Production Environment

```bash
# Build production image
docker build --target production -t inbox-zen-mcp:latest .

# Run with production settings
docker run -d \
  --name inbox-zen-prod \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8001:8001 \
  -e POSTMARK_WEBHOOK_SECRET=your_production_secret \
  -e LOG_LEVEL=WARNING \
  -e MAX_EMAIL_SIZE=5242880 \
  -v /var/log/inbox-zen:/app/logs \
  -v /var/lib/inbox-zen:/app/data \
  inbox-zen-mcp:latest
```

---

## 🔒 Security Configuration

### Production Security Checklist

- [ ] **Environment Variables:** Never commit secrets to version control
- [ ] **Webhook Secrets:** Use strong, randomly generated secrets
- [ ] **HTTPS:** Always use HTTPS in production
- [ ] **Firewall:** Restrict access to necessary ports only
- [ ] **Input Validation:** Enable all input validation features
- [ ] **Logging:** Configure secure logging without sensitive data
- [ ] **Updates:** Keep dependencies updated

### Security Configuration

```yaml
# Add to config.yaml
security:
  validate_postmark_signatures: true
  max_request_size: 10485760  # 10MB
  rate_limiting:
    enabled: true
    requests_per_minute: 60
  cors:
    enabled: false  # Disable in production
    allowed_origins: []
  headers:
    x_frame_options: "DENY"
    x_content_type_options: "nosniff"
    x_xss_protection: "1; mode=block"
```

---

## 📊 Monitoring and Health Checks

### Health Check Endpoint

```bash
# Check server health
curl http://localhost:8000/health

# Check webhook health
curl http://localhost:8001/health
```

### Monitoring Setup

```python
# Custom monitoring script
import requests
import time

def monitor_inbox_zen():
    endpoints = [
        "http://localhost:8000/health",
        "http://localhost:8001/health"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")

# Run monitoring
monitor_inbox_zen()
```

---

## 🔄 Maintenance

### Regular Maintenance Tasks

```bash
# Check logs
tail -f logs/inbox-zen.log

# Check email storage usage
python -c "from src.storage import get_email_stats; print(get_email_stats())"

# Cleanup old emails (if configured)
python -c "from src.storage import cleanup_old_emails; cleanup_old_emails()"

# Update dependencies
pip install --upgrade -r requirements.txt

# Run tests
pytest tests/ -v
```

### Backup and Recovery

```bash
# Backup email data (JSON format)
python -c "
from src.storage import get_all_emails
import json
with open('backup.json', 'w') as f:
    json.dump(get_all_emails(), f, indent=2, default=str)
"

# Restore from backup
python -c "
from src.storage import storage
import json
with open('backup.json', 'r') as f:
    emails = json.load(f)
    for email in emails:
        storage.store_email(email)
"
```

---

## 🆘 Support

### Getting Help

- **Documentation:** Check `/docs` folder for detailed guides
- **Logs:** Check `logs/inbox-zen.log` and `logs/errors.log`
- **Tests:** Run `pytest` to verify functionality
- **Health Checks:** Use `/health` endpoints for status

### Common Commands

```bash
# Test the complete system
python -m pytest tests/ -v

# Run integration tests
python test_integration_system.py

# Check performance
python simple_performance_test.py

# Debug storage issues
python simple_storage_test.py
```

This setup guide provides everything needed to get the Inbox Zen MCP Server running in any environment. For specific integration patterns and advanced usage, see the [Client Examples](client-examples.md) and [MCP Capabilities](mcp-capabilities.md) documentation.
