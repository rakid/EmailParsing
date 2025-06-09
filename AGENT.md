# AGENT.md - Inbox Zen Email Parsing MCP Server

## 🎯 Project Overview

**Inbox Zen** is a production-ready MCP server for intelligent email processing with **125 tests passing** (90% coverage). Currently 100% complete (Phase 1) with Supabase integration 80% complete (Phase 2).

**Key Features:**
- **🔌 MCP Data Source Server** - Full protocol compliance with resources, tools, and prompts
- **⚡ High-Performance** - Sub-10ms email processing, handles 1000+ emails/minute
- **🤖 Intelligent Analysis** - Multi-language regex patterns for urgency/sentiment detection
- **🔧 Plugin Architecture** - Extensible system for AI integrations (GPT-4, Claude, SambaNova)
- **🛡️ Production Security** - HMAC signature validation, input sanitization

## 📋 Commands

**Development/Testing:**
- `pytest` - Run all tests (125 tests)
- `pytest tests/core/test_extraction.py::TestEmailExtractor::test_extract_valid_email -v` - Run single test
- `pytest -m unit` - Run only unit tests  
- `pytest -m "not slow"` - Skip slow tests
- `pytest --cov=src --cov-report=html` - Run with coverage report

**Quality Assurance:**
- `python -m flake8 src/ tests/` - Lint code
- `python -m black src/ tests/` - Format code
- `python -m isort src/ tests/` - Sort imports
- `python -m mypy src/ --ignore-missing-imports` - Type check
- `./local_code_quality_check.sh` - Run all quality checks
- `bandit -r src/` - Security scan
- `safety check` - Dependency vulnerability scan

**Test Debugging:**
- `pytest tests/performance/test_performance.py::TestEmailProcessingPerformance::test_webhook_processing_performance -v` - Debug failing performance test
- `pytest tests/supabase_integration/test_plugin.py::TestSupabasePlugin::test_get_user_stats -v` - Debug failing stats test
- `pytest --lf` - Run only last failed tests
- `pytest --tb=long` - Detailed test failure output

**Server Operations:**
- `python -m src.server` - Start MCP server
- `python -m src.webhook` - Start webhook endpoint
- `curl http://localhost:8000/health` - Health check
- `curl http://localhost:8000/api/stats` - Processing statistics

**Deployment:**
- `docker build -t inbox-zen .` - Build Docker image
- `docker run -p 8000:8000 inbox-zen` - Run containerized
- `vercel` - Deploy to Vercel serverless

## 📁 Project Structure

```
src/
├── server.py                 # MCP server implementation
├── webhook.py                # Postmark webhook handler  
├── models.py                 # Pydantic data models
├── extraction.py             # Email analysis engine
├── integrations.py           # Plugin architecture
├── storage.py                # Data storage layer
├── config.py                 # Configuration management
└── supabase_integration/     # Supabase plugin (Phase 2)
    ├── database_interface.py # Database operations
    ├── auth_interface.py     # Authentication
    ├── realtime.py           # Real-time sync
    └── plugin.py             # Main plugin
```

## 🎨 Code Style Guidelines

**Formatting & Structure:**
- **Line length:** 88 characters (Black)
- **Imports:** Use isort with Black profile, group by stdlib/third-party/local
- **Types:** Use Pydantic models for data structures, type hints required
- **Naming:** snake_case for functions/variables, PascalCase for classes/Enums

**Development Patterns:**
- **Error handling:** Use try/except with specific exceptions, log errors appropriately
- **Async:** Use `@pytest.mark.asyncio` for async tests, asyncio_mode = "strict"
- **Test structure:** Organize tests in classes, use fixtures from conftest.py, mock external dependencies
- **Plugins:** Follow PluginInterface protocol for extensibility
- **MCP compliance:** Implement resources, tools, and prompts following MCP specification

**Tool Configurations:**
- **Black:** Line length 88 chars, skip string normalization disabled
  ```bash
  python -m black src/ tests/ --line-length 88
  ```
- **Flake8:** Max line length 88, ignore E203 (whitespace before ':'), W503 (line break before binary operator)
  ```bash
  python -m flake8 src/ tests/ --max-line-length=88 --ignore=E203,W503
  ```
- **MyPy:** Strict mode with ignore missing imports, check untyped definitions
  ```bash
  python -m mypy src/ --ignore-missing-imports --strict --warn-return-any
  ```
- **isort:** Black profile compatibility, force single line imports for from imports
  ```bash
  python -m isort src/ tests/ --profile black --force-single-line
  ```

**GitHub Copilot Configuration:**
- **Context files:** Include relevant test files and models.py for better suggestions
- **Prompt engineering:** Use descriptive function/variable names for better code generation
- **Code patterns:** Leverage existing patterns in extraction.py and integrations.py
- **Test generation:** Reference conftest.py fixtures and existing test structure
- **Async patterns:** Follow asyncio_mode = "strict" for async test suggestions
- **VS Code settings:** Enable Copilot suggestions in comments and strings
  ```json
  {
    "github.copilot.enable": {
      "*": true,
      "yaml": false,
      "plaintext": false
    },
    "github.copilot.inlineSuggest.enable": true,
    "github.copilot.editor.enableAutoCompletions": true
  }
  ```

**Security & Performance:**
- **Input validation:** Always use Pydantic models for request/response data
- **Authentication:** Verify webhook signatures using HMAC-SHA256
- **Rate limiting:** Implement for production endpoints (constants defined, implementation pending)
- **Logging:** Use structured JSON logging with appropriate levels (avoid debug print() in production)
- **Testing:** Maintain >85% code coverage (currently 85%, 2 failing tests to fix)
- **MCP Standards:** Follow MCP error response format, implement proper pagination
- **Production Readiness:** Remove debug code, complete TODOs before deployment

## 🔌 MCP Integration

**Available Tools:**
- `analyze_email` - Real-time email analysis
- `search_emails` - Filter and discover emails
- `get_email_stats` - Processing analytics
- `extract_tasks` - Action item identification
- `export_emails` - Data export (JSON/CSV/JSONL)
- `list_integrations` - Plugin discovery
- `process_through_plugins` - Enhanced processing

**Resources:**
- `email://processed` - All processed emails
- `email://stats` - Real-time statistics
- `email://high-urgency` - Urgent emails requiring attention

## 🚀 Deployment

**Environment Variables:**
- `POSTMARK_WEBHOOK_SECRET` - Webhook validation secret
- `ENVIRONMENT` - production/development
- `SUPABASE_URL` - Supabase project URL (Phase 2)
- `SUPABASE_KEY` - Supabase anon key (Phase 2)

**Current Status:**
- ✅ **Phase 1 Complete** - Core MCP server (17/17 tasks, 125 tests passing)
- 🔄 **Phase 2 Active** - Supabase integration (8/10 tasks, real-time features operational)
- 📋 **Documentation** - Comprehensive guides in docs/ folder

## 🚨 Known Issues & Fixes

**✅ Critical Issues Resolved (June 6, 2025):**
1. **✅ Performance test** - Added missing `from unittest.mock import patch` import 
2. **✅ Stats test** - Fixed mock structure to match actual `get_user_stats()` response format
3. **✅ Debug code** - Removed print() statements from production code

**Remaining Production Blockers:**
- Complete Supabase email invitation feature (marked TODO)
- Implement rate limiting (constants defined but not active)
- Fix real-time event triggering (test mode only)
- Add audit logging IP/User-Agent context

**Test Status:** 454 passing, 0 failing, 2 skipped (100% critical tests resolved)
