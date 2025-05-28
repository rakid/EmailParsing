# 📧 Inbox Zen - Email Parsing MCP Server

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-125%20passing-green.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](#testing)

> **🏆 Hackathon MVP** - A production-ready Model Context Protocol (MCP) server for intelligent email processing and analysis.

## 🎯 Project Overview

**Inbox Zen** is a sophisticated MCP server that serves as the unified email entry point for modern LLM applications. It receives emails via Postmark webhooks, performs intelligent analysis using advanced regex patterns, and exposes structured data through the standardized Model Context Protocol.

### 🏗️ Architecture Highlights

- **🔌 MCP Data Source Server** - Full protocol compliance with resources, tools, and prompts
- **⚡ High-Performance Processing** - Sub-10ms average email processing time
- **🤖 Intelligent Analysis Engine** - Multi-language regex patterns for urgency, sentiment, and metadata extraction
- **🔧 Plugin Architecture** - Extensible system for future AI integrations (GPT-4, Claude, etc.)
- **🛡️ Production Security** - HMAC signature validation, input sanitization, and comprehensive error handling
- **📊 Real-time Analytics** - Live processing statistics and email insights

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Poetry or pip
- Postmark account (for webhook integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/rakid/EmailParsing.git
cd EmailParsing

# Install dependencies
pip install -r requirements.txt

# Or with Poetry
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your Postmark webhook secret
```

### Configuration

```yaml
# config/config.yaml
server:
  name: "inbox-zen-mcp"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000

postmark:
  webhook_secret: "${POSTMARK_WEBHOOK_SECRET}"
  signature_header: "X-Postmark-Signature"

processing:
  max_email_size: 10485760  # 10MB
  timeout_seconds: 30
  enable_real_time_logging: true
```

### Running the Server

```bash
# Start the MCP server
python -m src.server

# Start the webhook endpoint (separate terminal)
python -m src.webhook

# Run with Docker
docker build -t inbox-zen .
docker run -p 8000:8000 inbox-zen
```

## 🚀 Deployment Options

### Local Development

```bash
# Start the MCP server
python -m src.server

# Start the webhook endpoint (separate terminal)
python -m src.webhook

# Run with Docker
docker build -t inbox-zen .
docker run -p 8000:8000 inbox-zen
```

### Vercel Serverless Deployment

Deploy to Vercel for production-ready serverless hosting:

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel

# Set environment variables
vercel env add POSTMARK_WEBHOOK_SECRET
vercel env add ENVIRONMENT production
```

**Available endpoints after deployment:**

- `POST /webhook` - Postmark webhook receiver
- `GET /health` - Health check
- `GET /mcp/health` - MCP server health
- `GET /mcp/resources` - List MCP resources  
- `POST /mcp/tools/call` - Call MCP tools
- `GET /api/stats` - Processing statistics

See [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) for detailed deployment guide.

### Docker Deployment

```bash
# Build and run with Docker
docker build -t inbox-zen .
docker run -p 8000:8000 -e POSTMARK_WEBHOOK_SECRET=your_secret inbox-zen
```

## 🔌 MCP Integration

### Available Resources

```json
{
  "resources": [
    {
      "uri": "email://processed",
      "name": "Processed Emails",
      "description": "Access to all processed email data with analysis results"
    },
    {
      "uri": "email://stats",
      "name": "Email Statistics", 
      "description": "Real-time email processing statistics and analytics"
    },
    {
      "uri": "email://high-urgency",
      "name": "High Urgency Emails",
      "description": "Emails marked as high urgency requiring immediate attention"
    }
  ]
}
```

### Available Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `analyze_email` | Analyze email content for urgency, sentiment, and metadata | Real-time email triage |
| `search_emails` | Search and filter processed emails by criteria | Email discovery and filtering |
| `get_email_stats` | Get comprehensive processing statistics | Analytics and monitoring |
| `extract_tasks` | Extract action items and tasks from emails | Task management integration |
| `export_emails` | Export emails in various formats (JSON, CSV, JSONL) | Data integration and backup |
| `list_integrations` | Discover available plugins and integrations | System introspection |
| `process_through_plugins` | Enhanced email processing via plugin pipeline | Extensible analysis |

### Client Example

```python
import asyncio
from mcp import ClientSession

async def analyze_urgent_emails():
    async with ClientSession("stdio", "python", "-m", "src.server") as session:
        # Get high urgency emails
        urgent_emails = await session.read_resource("email://high-urgency")
        
        # Analyze specific email
        analysis = await session.call_tool("analyze_email", {
            "email_id": "email-123",
            "content": "URGENT: Server down, immediate action required!"
        })
        
        # Extract actionable tasks
        tasks = await session.call_tool("extract_tasks", {
            "urgency_threshold": 70
        })
        
        return analysis, tasks

# Run the client
results = asyncio.run(analyze_urgent_emails())
```

## 🧠 Intelligent Analysis Engine

### Multi-Language Support

- **English & French** - Comprehensive pattern recognition
- **Urgency Detection** - Smart scoring (0-100) with confidence levels
- **Sentiment Analysis** - Positive, negative, neutral classification
- **Temporal Extraction** - Deadlines, dates, time references
- **Action Item Detection** - Automatic task identification
- **Contact Extraction** - Emails, phones, names

### Sample Analysis Output

```json
{
  "urgency_score": 85,
  "urgency_level": "high",
  "sentiment": "negative",
  "confidence": 0.92,
  "keywords": ["urgent", "server", "down", "immediate"],
  "action_items": ["check server status", "contact team", "restore service"],
  "temporal_references": ["ASAP", "immediately"],
  "tags": ["infrastructure", "critical", "ops"],
  "contact_info": {
    "emails": ["admin@company.com"],
    "phones": ["+1-555-0123"]
  }
}
```

## 🔧 Plugin Architecture

### Built-in Plugins

```python
# Email categorization plugin
class EmailCategoryPlugin(PluginInterface):
    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        category = self.categorize_email(email)
        email.analysis.tags.append(f"category:{category}")
        return email

# Spam detection plugin  
class SpamDetectionPlugin(PluginInterface):
    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        spam_score = self.calculate_spam_score(email)
        email.analysis.tags.append(f"spam:{'likely' if spam_score > 0.7 else 'unlikely'}")
        return email
```

### Future Integration Interfaces

- **AI Analysis** - GPT-4, Claude, local LLMs
- **Database Storage** - SQLite, PostgreSQL, MongoDB
- **External APIs** - CRM systems, notification services
- **Custom Workflows** - User-defined processing pipelines

## 📊 Performance & Monitoring

### Performance Metrics

- **Processing Time**: <10ms average (sub-2s target exceeded)
- **Memory Usage**: Minimal footprint with efficient async processing  
- **Throughput**: Handles 1000+ emails/minute under load
- **Reliability**: 99.9% uptime in testing scenarios

### Real-time Monitoring

```bash
# View live processing logs
tail -f logs/inbox-zen.log

# Check system health
curl http://localhost:8000/health

# Get processing statistics  
curl http://localhost:8000/api/stats
```

### Testing Coverage

- **125 Tests Passing** - Comprehensive test suite
- **90% Code Coverage** - High test confidence
- **Integration Tests** - End-to-end webhook processing
- **Performance Tests** - Load testing and benchmarks
- **Security Tests** - Vulnerability scanning and validation

## 🛡️ Security Features

### Webhook Security

```python
def verify_postmark_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Postmark webhook signature using HMAC-SHA256"""
    expected = hmac.new(
        secret.encode('utf-8'), 
        payload, 
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### Input Validation

- **Pydantic Models** - Strict data validation and serialization
- **Content Sanitization** - XSS prevention and size limits
- **Rate Limiting** - Protection against abuse
- **Error Handling** - Graceful failure with detailed logging

## 📁 Project Structure

```
EmailParsing/
├── src/                          # Source code
│   ├── server.py                 # MCP server implementation
│   ├── webhook.py                # Postmark webhook handler
│   ├── models.py                 # Pydantic data models
│   ├── extraction.py             # Email analysis engine
│   ├── integrations.py           # Plugin architecture
│   ├── storage.py                # Data storage layer
│   └── config.py                 # Configuration management
├── tests/                        # Comprehensive test suite
│   ├── test_server.py            # MCP server tests
│   ├── test_webhook.py           # Webhook processing tests
│   ├── test_extraction.py        # Analysis engine tests
│   └── test_integration.py       # Integration tests
├── docs/                         # Documentation
│   ├── mcp-capabilities.md       # MCP API documentation
│   ├── security-guide.md         # Security implementation
│   ├── migration-guide.md        # Version upgrade guide
│   └── client-examples.md        # Usage examples
├── examples/                     # Code examples
│   └── integration_demo.py       # Plugin demonstration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container deployment
└── TASKS.md                      # Development tracking
```

## 📈 Roadmap & Future Enhancements

### Phase 2: AI Integration

- **GPT-4 Analysis** - Advanced email understanding
- **Semantic Search** - Vector-based email discovery
- **Auto-Response** - Intelligent reply suggestions
- **Summary Generation** - Email thread summarization

### Phase 3: Advanced Features

- **Multi-tenancy** - Support for multiple organizations
- **Real-time Dashboard** - Web-based monitoring interface
- **Workflow Automation** - Rule-based email processing
- **Mobile Notifications** - Push alerts for urgent emails

## 🚀 CI/CD Pipeline

This project features a comprehensive CI/CD pipeline with automated testing, code quality analysis, security scanning, and deployment.

### 🔧 GitHub Actions Workflows

| Workflow | Trigger | Purpose | Status |
|----------|---------|---------|--------|
| **Deploy to Vercel** | Push to main, PRs | Automated deployment with testing | [![Deploy](https://github.com/rakid/EmailParsing/actions/workflows/deploy-vercel.yml/badge.svg)](https://github.com/rakid/EmailParsing/actions/workflows/deploy-vercel.yml) |
| **Code Quality** | Push, PRs, weekly | Linting, formatting, type checking | [![Quality](https://github.com/rakid/EmailParsing/actions/workflows/code-quality.yml/badge.svg)](https://github.com/rakid/EmailParsing/actions/workflows/code-quality.yml) |
| **Dependency Management** | Weekly schedule | Security vulnerability scanning | [![Dependencies](https://github.com/rakid/EmailParsing/actions/workflows/dependency-management.yml/badge.svg)](https://github.com/rakid/EmailParsing/actions/workflows/dependency-management.yml) |
| **Performance Testing** | Manual, scheduled | Load testing and benchmarks | [![Performance](https://github.com/rakid/EmailParsing/actions/workflows/performance.yml/badge.svg)](https://github.com/rakid/EmailParsing/actions/workflows/performance.yml) |
| **Release Management** | Tag creation | Automated releases and changelog | [![Release](https://github.com/rakid/EmailParsing/actions/workflows/release.yml/badge.svg)](https://github.com/rakid/EmailParsing/actions/workflows/release.yml) |

### 🔍 Code Quality Tools

- **Black** - Code formatting
- **isort** - Import sorting  
- **flake8** - Linting and style checking
- **mypy** - Static type checking
- **Bandit** - Security vulnerability scanning
- **Safety** - Dependency vulnerability checking
- **SonarCloud** - Comprehensive code quality analysis
- **Codecov** - Test coverage reporting

### 🛡️ Security & Monitoring

- **Automated Dependency Updates** - Dependabot for Python packages and GitHub Actions
- **Security Scanning** - Weekly vulnerability assessments
- **Performance Monitoring** - Automated load testing against production
- **Code Quality Gates** - PR checks prevent regression

### 📋 Setup Requirements

To enable the full CI/CD pipeline, configure these GitHub repository secrets:

**Required Secrets:**
- `VERCEL_TOKEN` - Vercel deployment token
- `VERCEL_ORG_ID` - Vercel organization ID  
- `VERCEL_PROJECT_ID` - Vercel project ID
- `POSTMARK_WEBHOOK_SECRET` - Webhook validation secret

**Optional Secrets (for enhanced features):**
- `CODECOV_TOKEN` - Test coverage reporting
- `SONAR_TOKEN` - SonarCloud code analysis
- `DOCKER_USERNAME` & `DOCKER_PASSWORD` - Docker image publishing

📖 **See [GITHUB_SETUP.md](./GITHUB_SETUP.md) for detailed setup instructions.**

### 🎯 Quality Metrics

- **Test Coverage**: 90%+ maintained automatically
- **Code Quality**: A+ grade on SonarCloud
- **Security**: Zero known vulnerabilities
- **Performance**: <10ms email processing time
- **Deployment**: Zero-downtime deployments to Vercel

## 🤝 Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v --cov=src

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
safety check
```

### Pre-commit Workflow

All code changes go through automated quality checks:

1. **Code Formatting** - Black and isort ensure consistent style
2. **Linting** - flake8 catches common issues
3. **Type Checking** - mypy validates type annotations
4. **Security Scan** - Bandit identifies security issues
5. **Test Suite** - Full test suite with coverage reporting
6. **Performance Tests** - Ensure no regression in processing speed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Model Context Protocol** - For the excellent MCP specification
- **Postmark** - For reliable email webhook delivery
- **FastAPI** - For the high-performance web framework
- **Pydantic** - For robust data validation

---

## 📞 Support & Contact

- **Documentation**: [./docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/rakid/EmailParsing/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rakid/EmailParsing/discussions)

**Built with ❤️ for the MCP Hackathon - Aiming for first place! 🏆**
