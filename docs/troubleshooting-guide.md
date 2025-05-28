# 🛠️ Troubleshooting & Debugging Guide

Comprehensive troubleshooting guide for the Inbox Zen Email Parsing MCP Server. This guide covers common issues, debugging techniques, and solutions for both development and production environments.

---

## 🚨 Quick Issue Resolution

### Common Problems & Quick Fixes

| Problem | Quick Fix | Details |
|---------|-----------|---------|
| MCP server won't start | Check Python path and dependencies | See [Server Startup Issues](#server-startup-issues) |
| Webhook not receiving emails | Verify Postmark configuration | See [Webhook Issues](#webhook-issues) |
| Import errors | Check relative imports and PYTHONPATH | See [Import Issues](#import-issues) |
| Emails not being processed | Check webhook signature validation | See [Processing Issues](#processing-issues) |
| High memory usage | Review storage cleanup settings | See [Performance Issues](#performance-issues) |

---

## 🔍 Diagnostic Commands

### System Health Check

```bash
# Complete system diagnostic
python -c "
import sys
print('Python version:', sys.version)

try:
    from src import server, webhook, storage
    print('✅ Core modules: OK')
except ImportError as e:
    print('❌ Core modules:', e)

try:
    from src.integrations import integration_registry
    print('✅ Integrations: OK')
except ImportError as e:
    print('⚠️ Integrations:', e)

try:
    import mcp
    print('✅ MCP SDK: OK')
except ImportError:
    print('❌ MCP SDK: Not installed')

print('Current directory:', sys.path[0])
"
```

### Quick Test Suite

```bash
# Run critical tests only
python -m pytest tests/test_server.py::test_mcp_server_initialization -v
python -m pytest tests/test_storage.py::test_store_and_retrieve_email -v
python -m pytest tests/test_webhook.py::test_webhook_endpoint -v

# Test integration system
python simple_integration_test.py

# Test storage isolation
python simple_storage_test.py
```

### Log Analysis

```bash
# Check recent errors
tail -n 50 logs/errors.log

# Monitor real-time logs
tail -f logs/inbox-zen.log

# Search for specific issues
grep -i "error\|exception\|failed" logs/inbox-zen.log | tail -10
grep -i "webhook" logs/inbox-zen.log | tail -5
grep -i "processing" logs/inbox-zen.log | tail -5
```

---

## 🚫 Server Startup Issues

### Problem: Server Won't Start

#### Symptoms
- `ModuleNotFoundError` when starting server
- `ImportError` for MCP or internal modules  
- Server exits immediately without error

#### Diagnosis

```bash
# Check Python environment
python --version  # Should be 3.12+
which python

# Verify installation
pip list | grep -E "mcp|fastapi|pydantic"

# Test basic imports
python -c "import mcp; print('MCP SDK OK')"
python -c "from src import server; print('Server module OK')"
```

#### Solutions

```bash
# Solution 1: Fix Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m src.server

# Solution 2: Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Solution 3: Use absolute paths
cd /path/to/EmailParsing
python -m src.server

# Solution 4: Virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.server
```

### Problem: MCP Protocol Errors

#### Symptoms
- Client can't connect to MCP server
- Protocol version mismatch
- JSON-RPC errors

#### Diagnosis

```bash
# Test MCP server directly
python -c "
from src.server import server
import asyncio

async def test_mcp():
    # Test server initialization
    print('Server name:', server.name)
    print('Server version:', server.version)
    
    # Test capabilities
    resources = await server.list_resources()
    print('Resources:', len(resources))
    
    tools = await server.list_tools()
    print('Tools:', len(tools))

asyncio.run(test_mcp())
"
```

#### Solutions

```bash
# Update MCP SDK
pip install --upgrade mcp

# Check protocol compatibility
python -c "import mcp; print('MCP version:', mcp.__version__)"

# Restart with debug logging
LOG_LEVEL=DEBUG python -m src.server
```

---

## 📡 Webhook Issues

### Problem: Webhooks Not Being Received

#### Symptoms
- Postmark shows webhooks sent but server doesn't process them
- 404 or connection errors from Postmark
- Webhook endpoint not responding

#### Diagnosis

```bash
# Test webhook endpoint
curl -X POST http://localhost:8001/webhook \
  -H "Content-Type: application/json" \
  -H "X-Postmark-Signature: sha256=test" \
  -d '{"test": "ping"}'

# Check webhook server status
curl http://localhost:8001/health

# Test network connectivity
netstat -tuln | grep 8001
```

#### Solutions

```bash
# Solution 1: Start webhook server
python -m src.webhook

# Solution 2: Check firewall
sudo ufw status
sudo ufw allow 8001

# Solution 3: Bind to all interfaces
# Edit webhook.py to use host='0.0.0.0'

# Solution 4: Use different port
PORT=8002 python -m src.webhook
```

### Problem: Signature Validation Failing

#### Symptoms
- Webhooks received but rejected with authentication errors
- "Invalid signature" in logs
- HTTP 401 responses

#### Diagnosis

```bash
# Check webhook secret configuration
python -c "
import os
from src.config import config
print('Webhook secret configured:', bool(config.postmark_webhook_secret))
print('Secret length:', len(config.postmark_webhook_secret or ''))
"

# Test signature generation
python -c "
import hmac
import hashlib
import base64

secret = 'your_secret_here'
payload = '{\"test\": \"data\"}'
signature = base64.b64encode(
    hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
).decode()
print('Expected signature:', f'sha256={signature}')
"
```

#### Solutions

```bash
# Solution 1: Update webhook secret
export POSTMARK_WEBHOOK_SECRET="your_correct_secret"

# Solution 2: Disable validation for testing
# Edit config.yaml: postmark.validate_signatures: false

# Solution 3: Check Postmark webhook settings
# Ensure secret matches in Postmark dashboard

# Solution 4: Debug signature calculation
python debug_webhook_signature.py
```

---

## 🔄 Processing Issues

### Problem: Emails Not Being Analyzed

#### Symptoms
- Emails stored but analysis fields empty
- Processing time is 0
- No urgency/sentiment detection

#### Diagnosis

```bash
# Test analysis engine
python -c "
from src.extraction import email_extractor

test_email = {
    'subject': 'URGENT: Please review this immediately',
    'text_body': 'This is an urgent task that needs immediate attention. Please complete by tomorrow.'
}

analysis = email_extractor.analyze_email(test_email)
print('Urgency:', analysis.urgency_level)
print('Sentiment:', analysis.sentiment)
print('Tasks:', analysis.extracted_tasks)
"

# Check regex patterns
python -c "
from src.extraction import email_extractor
print('Urgency patterns loaded:', len(email_extractor.urgency_patterns))
print('Task patterns loaded:', len(email_extractor.task_patterns))
"
```

#### Solutions

```bash
# Solution 1: Verify extraction module
python -c "from src.extraction import email_extractor; print('✅ Extraction module OK')"

# Solution 2: Test with simple email
python simple_debug.py

# Solution 3: Check language detection
pip install langdetect

# Solution 4: Reset analysis patterns
# Remove custom patterns and test with defaults
```

### Problem: High Processing Time

#### Symptoms
- Processing time > 1 second per email
- Timeouts during analysis
- High CPU usage

#### Diagnosis

```bash
# Profile processing performance
python -c "
import time
from src.extraction import email_extractor

test_email = {
    'subject': 'Test email subject',
    'text_body': 'Test email body content.'
}

start_time = time.time()
analysis = email_extractor.analyze_email(test_email)
processing_time = time.time() - start_time

print(f'Processing time: {processing_time:.4f}s')
print('Expected: < 0.1s')
"

# Check regex complexity
python -c "
from src.extraction import email_extractor
import re

for pattern in email_extractor.urgency_patterns:
    try:
        re.compile(pattern, re.IGNORECASE)
        print(f'✅ Pattern OK: {pattern[:50]}')
    except re.error as e:
        print(f'❌ Pattern error: {pattern[:50]} - {e}')
"
```

#### Solutions

```bash
# Solution 1: Optimize regex patterns
# Review and simplify complex patterns

# Solution 2: Add processing timeout
# Set processing.timeout_seconds in config

# Solution 3: Profile with detailed tools
pip install memory-profiler
python -m memory_profiler simple_performance_test.py

# Solution 4: Batch processing
# Process multiple emails together instead of individually
```

---

## 💾 Storage Issues

### Problem: Storage Sharing Between Modules

#### Symptoms
- Webhook stores emails but MCP server can't see them
- Inconsistent email counts between tools
- Storage isolation errors

#### Diagnosis

```bash
# Test storage isolation
python simple_storage_test.py

# Check storage state
python -c "
from src.storage import storage
print('Storage type:', type(storage))
print('Email count:', len(storage.emails))

# Test from different modules
import sys
sys.path.append('src')

from webhook import storage as webhook_storage
from server import storage as server_storage

print('Webhook storage emails:', len(webhook_storage.emails))
print('Server storage emails:', len(server_storage.emails))
print('Same instance:', webhook_storage is server_storage)
"
```

#### Solutions

```bash
# Solution 1: Use singleton pattern (already implemented)
# Verify with simple_storage_test.py

# Solution 2: Clear storage and restart
python -c "from src.storage import storage; storage.clear_all_emails()"

# Solution 3: Test with fresh environment
# Remove __pycache__ and restart
rm -rf src/__pycache__ __pycache__
python -m src.server

# Solution 4: Force storage sync
python -c "
from src.storage import storage
storage.store_email({
    'id': 'test',
    'data': {'subject': 'test'},
    'analysis': {},
    'timestamp': '2025-05-28T10:00:00Z'
})
print('Test email stored:', len(storage.emails))
"
```

### Problem: Storage Limit Exceeded

#### Symptoms
- Emails not being stored
- "Storage limit exceeded" errors
- Memory usage keeps growing

#### Diagnosis

```bash
# Check storage usage
python -c "
from src.storage import get_email_stats
stats = get_email_stats()
print('Total emails:', stats['total_processed'])
print('Storage limit:', getattr(storage, 'max_emails', 'Not set'))
"

# Check memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

#### Solutions

```bash
# Solution 1: Increase storage limit
# Edit config.yaml: storage.max_emails: 2000

# Solution 2: Enable automatic cleanup
# Edit config.yaml: storage.cleanup_interval_hours: 24

# Solution 3: Manual cleanup
python -c "
from src.storage import storage
old_count = len(storage.emails)
storage.cleanup_old_emails(keep_last=500)
new_count = len(storage.emails)
print(f'Cleaned up {old_count - new_count} emails')
"

# Solution 4: External storage
# Implement database backend instead of in-memory storage
```

---

## 🔌 Integration Issues

### Problem: Import Path Errors

#### Symptoms
- `ModuleNotFoundError` in integration modules
- Relative import errors
- Integration features not available

#### Diagnosis

```bash
# Test integration imports
python -c "
try:
    from src.integrations import integration_registry
    print('✅ Integration registry imported')
    print('Available integrations:', len(integration_registry.list_integrations()))
except ImportError as e:
    print('❌ Integration import error:', e)
"

# Check import paths
python -c "
import sys
print('Python path:')
for path in sys.path:
    print(' ', path)
    
print('\\nCurrent directory:', sys.path[0])
"
```

#### Solutions

```bash
# Solution 1: Fix relative imports (already done)
# All imports should use relative paths like "from .models import"

# Solution 2: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Solution 3: Use absolute imports for testing
cd /path/to/EmailParsing
python -c "import src.integrations"

# Solution 4: Test integration system
python test_integration_system.py
```

### Problem: Plugin System Not Working

#### Symptoms
- Plugins not loading
- Plugin processing fails
- Missing plugin tools in MCP server

#### Diagnosis

```bash
# Test plugin system
python -c "
from src.integrations import PluginManager

manager = PluginManager()
plugins = manager.list_plugins()
print('Available plugins:', [p.get_name() for p in plugins])

# Test plugin processing
if plugins:
    test_email = {
        'id': 'test',
        'data': {'subject': 'test'},
        'analysis': {}
    }
    result = manager.process_through_plugins(['example_plugin'], test_email)
    print('Plugin processing result:', result)
"
```

#### Solutions

```bash
# Solution 1: Verify plugin registration
# Check that plugins are properly registered in integrations.py

# Solution 2: Test individual plugins
python -c "
from src.integrations import ExampleAnalysisPlugin
plugin = ExampleAnalysisPlugin()
print('Plugin name:', plugin.get_name())
"

# Solution 3: Enable integration features
# Edit config.yaml: integrations.enable_plugins: true

# Solution 4: Debug plugin loading
python debug_integration_helpers.py
```

---

## ⚡ Performance Issues

### Problem: High Memory Usage

#### Symptoms
- Memory usage grows over time
- Server becomes slow or unresponsive
- Out of memory errors

#### Diagnosis

```bash
# Monitor memory usage
python -c "
import psutil
import os
import time

process = psutil.Process(os.getpid())
for i in range(5):
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f'Memory usage: {memory_mb:.2f} MB')
    time.sleep(1)
"

# Profile memory usage
pip install memory-profiler
python -m memory_profiler comprehensive_performance_test.py
```

#### Solutions

```bash
# Solution 1: Enable storage cleanup
python -c "
from src.config import config
config.storage['cleanup_interval_hours'] = 1
"

# Solution 2: Reduce storage limit
# Edit config.yaml: storage.max_emails: 100

# Solution 3: Use external storage
# Implement database storage instead of in-memory

# Solution 4: Add garbage collection
python -c "
import gc
gc.collect()
print('Garbage collection completed')
"
```

### Problem: Slow Processing

#### Symptoms
- Processing time > 100ms per email
- Webhook timeouts
- High CPU usage

#### Diagnosis

```bash
# Run performance tests
python simple_performance_test.py

# Profile processing time
python -c "
import cProfile
import time
from src.extraction import email_extractor

def test_processing():
    email = {
        'subject': 'URGENT: Review this project immediately',
        'text_body': 'Please review and complete the quarterly report by tomorrow. This is critical for our deadline.'
    }
    
    start = time.time()
    analysis = email_extractor.analyze_email(email)
    end = time.time()
    
    print(f'Processing time: {(end - start) * 1000:.2f}ms')
    return analysis

cProfile.run('test_processing()')
"
```

#### Solutions

```bash
# Solution 1: Optimize regex patterns
# Simplify complex regex patterns in extraction.py

# Solution 2: Add caching
# Cache compiled regex patterns and analysis results

# Solution 3: Use async processing
# Process emails asynchronously where possible

# Solution 4: Batch processing
# Process multiple emails in batches
```

---

## 🐛 Debugging Tools

### Custom Debugging Scripts

#### Email Processing Debug

```python
# debug_email_processing.py
from src.extraction import email_extractor
from src.storage import storage
import json

def debug_email_processing():
    test_email = {
        'from': 'test@example.com',
        'to': ['inbox@yourapp.com'],
        'subject': 'URGENT: Critical system failure - immediate action required',
        'text_body': '''
        We have detected a critical system failure that requires immediate attention.
        
        Action items:
        1. Please investigate the database connection issues
        2. Restart the application servers
        3. Notify the development team immediately
        
        This must be completed within the next 2 hours to prevent data loss.
        
        Contact me ASAP if you need assistance.
        
        Best regards,
        System Administrator
        ''',
        'headers': {'message-id': 'debug-test-123'},
        'date': '2025-05-28T10:30:00Z'
    }
    
    print("🔍 Processing test email...")
    print(f"Subject: {test_email['subject']}")
    print(f"Body length: {len(test_email['text_body'])} characters")
    
    # Analyze email
    analysis = email_extractor.analyze_email(test_email)
    
    print("\n📊 Analysis Results:")
    print(f"Urgency Level: {analysis.urgency_level}")
    print(f"Urgency Score: {analysis.urgency_score:.3f}")
    print(f"Sentiment: {analysis.sentiment}")
    print(f"Sentiment Score: {analysis.sentiment_score:.3f}")
    print(f"Language: {analysis.language}")
    print(f"Processing Time: {analysis.processing_time:.3f}s")
    
    print(f"\n🔑 Keywords: {', '.join(analysis.keywords)}")
    
    print(f"\n✅ Extracted Tasks ({len(analysis.extracted_tasks)}):")
    for i, task in enumerate(analysis.extracted_tasks, 1):
        print(f"  {i}. {task['task']} (confidence: {task['confidence']:.3f})")
    
    # Test storage
    processed_email = {
        'id': 'debug-test-123',
        'timestamp': '2025-05-28T10:30:00Z',
        'data': test_email,
        'analysis': analysis.__dict__
    }
    
    storage.store_email(processed_email)
    print(f"\n💾 Email stored. Total emails in storage: {len(storage.emails)}")
    
    # Test retrieval
    retrieved = storage.get_email('debug-test-123')
    if retrieved:
        print("✅ Email retrieval: Success")
    else:
        print("❌ Email retrieval: Failed")

if __name__ == "__main__":
    debug_email_processing()
```

#### Storage Debug

```python
# debug_storage_detailed.py
from src.storage import storage
from src.models import ProcessedEmail, EmailData, EmailAnalysis
import json

def debug_storage_detailed():
    print("🔍 Storage Debug - Detailed Analysis")
    print(f"Storage type: {type(storage)}")
    print(f"Storage ID: {id(storage)}")
    
    # Test email data
    test_emails = [
        {
            'id': 'test-1',
            'timestamp': '2025-05-28T10:00:00Z',
            'data': {
                'from': 'user1@example.com',
                'to': ['inbox@app.com'],
                'subject': 'Test Email 1',
                'text_body': 'This is test email 1 content.'
            },
            'analysis': {
                'urgency_level': 'medium',
                'urgency_score': 0.5,
                'sentiment': 'neutral',
                'sentiment_score': 0.0,
                'extracted_tasks': [],
                'keywords': ['test'],
                'language': 'en',
                'processing_time': 0.001
            }
        },
        {
            'id': 'test-2', 
            'timestamp': '2025-05-28T10:01:00Z',
            'data': {
                'from': 'user2@example.com',
                'to': ['inbox@app.com'],
                'subject': 'URGENT: Test Email 2',
                'text_body': 'This is urgent test email 2 content.'
            },
            'analysis': {
                'urgency_level': 'high',
                'urgency_score': 0.9,
                'sentiment': 'negative',
                'sentiment_score': -0.3,
                'extracted_tasks': [{'task': 'respond urgently', 'confidence': 0.8}],
                'keywords': ['urgent', 'test'],
                'language': 'en', 
                'processing_time': 0.002
            }
        }
    ]
    
    print(f"\n📧 Storing {len(test_emails)} test emails...")
    
    # Store emails
    for email in test_emails:
        storage.store_email(email)
        print(f"  ✅ Stored: {email['id']}")
    
    print(f"\n📊 Storage Status:")
    print(f"  Total emails: {len(storage.emails)}")
    print(f"  Email IDs: {list(storage.emails.keys())}")
    
    # Test retrieval
    print(f"\n🔍 Testing Retrieval:")
    for email_id in ['test-1', 'test-2', 'nonexistent']:
        retrieved = storage.get_email(email_id)
        if retrieved:
            print(f"  ✅ {email_id}: Found (subject: {retrieved['data']['subject']})")
        else:
            print(f"  ❌ {email_id}: Not found")
    
    # Test filtering
    print(f"\n🔧 Testing Filters:")
    urgent_emails = storage.get_emails_by_urgency('high')
    print(f"  High urgency emails: {len(urgent_emails)}")
    
    recent_emails = storage.get_recent_emails(limit=1)
    print(f"  Recent emails (limit 1): {len(recent_emails)}")
    
    # Test statistics
    print(f"\n📈 Testing Statistics:")
    from src.storage import get_email_stats
    stats = get_email_stats()
    print(f"  Total processed: {stats.get('total_processed', 0)}")
    print(f"  Total urgent: {stats.get('total_urgent', 0)}")
    
    # Memory usage
    import sys
    storage_size = sys.getsizeof(storage.emails)
    print(f"\n💾 Memory Usage:")
    print(f"  Storage dict size: {storage_size} bytes")
    print(f"  Average per email: {storage_size / max(len(storage.emails), 1):.1f} bytes")

if __name__ == "__main__":
    debug_storage_detailed()
```

### Log Analysis Scripts

```bash
# analyze_logs.sh
#!/bin/bash

echo "📊 Log Analysis Report"
echo "====================="

# Check if log files exist
if [ ! -f "logs/inbox-zen.log" ]; then
    echo "❌ Main log file not found: logs/inbox-zen.log"
    exit 1
fi

echo "📈 Log Statistics:"
echo "  Total log entries: $(wc -l < logs/inbox-zen.log)"
echo "  Error entries: $(grep -c -i 'error' logs/inbox-zen.log || echo 0)"
echo "  Warning entries: $(grep -c -i 'warning' logs/inbox-zen.log || echo 0)"
echo "  Info entries: $(grep -c -i 'info' logs/inbox-zen.log || echo 0)"

echo -e "\n🚨 Recent Errors (last 10):"
grep -i 'error' logs/inbox-zen.log | tail -10 || echo "  No errors found"

echo -e "\n⚠️ Recent Warnings (last 5):"
grep -i 'warning' logs/inbox-zen.log | tail -5 || echo "  No warnings found"

echo -e "\n📧 Email Processing Activity (last 10):"
grep -i 'processing\|webhook\|email' logs/inbox-zen.log | tail -10 || echo "  No processing activity found"

echo -e "\n🔍 Performance Indicators:"
echo "  Processing times > 100ms:"
grep -E 'processing.*[0-9]+\.[0-9]+s' logs/inbox-zen.log | \
  awk '{if ($NF > 0.1) print}' | wc -l || echo "0"

echo -e "\n📊 Most Recent Activity:"
tail -5 logs/inbox-zen.log || echo "  No recent activity"
```

### Test Scripts

```bash
# run_diagnostics.sh
#!/bin/bash

echo "🔧 Inbox Zen Diagnostics"
echo "========================"

# Test 1: Basic imports
echo "1. Testing basic imports..."
python -c "
try:
    from src import server, webhook, storage, models, extraction
    print('  ✅ All core modules imported successfully')
except ImportError as e:
    print(f'  ❌ Import error: {e}')
"

# Test 2: MCP server
echo -e "\n2. Testing MCP server..."
python -c "
try:
    from src.server import server
    print(f'  ✅ MCP server initialized: {server.name}')
except Exception as e:
    print(f'  ❌ MCP server error: {e}')
"

# Test 3: Storage system
echo -e "\n3. Testing storage system..."
python simple_storage_test.py

# Test 4: Integration system
echo -e "\n4. Testing integration system..."
python simple_integration_test.py

# Test 5: Performance
echo -e "\n5. Running performance test..."
python simple_performance_test.py

# Test 6: Health checks
echo -e "\n6. Testing health endpoints..."
if command -v curl &> /dev/null; then
    # Start servers in background for testing
    python -m src.server &
    SERVER_PID=$!
    python -m src.webhook &
    WEBHOOK_PID=$!
    
    sleep 2
    
    echo "  Testing MCP server health..."
    curl -s http://localhost:8000/health > /dev/null && echo "  ✅ MCP server responding" || echo "  ❌ MCP server not responding"
    
    echo "  Testing webhook server health..."
    curl -s http://localhost:8001/health > /dev/null && echo "  ✅ Webhook server responding" || echo "  ❌ Webhook server not responding"
    
    # Cleanup
    kill $SERVER_PID $WEBHOOK_PID 2>/dev/null
else
    echo "  ⚠️ curl not available, skipping health checks"
fi

echo -e "\n✅ Diagnostics complete!"
```

---

## 📞 Getting Help

### Support Checklist

Before seeking help, please gather the following information:

- [ ] Python version (`python --version`)
- [ ] Operating system and version
- [ ] Error messages from logs
- [ ] Steps to reproduce the issue
- [ ] Configuration files (with secrets redacted)
- [ ] Output from diagnostic commands

### Useful Commands for Support

```bash
# Environment information
python --version
pip list | grep -E "mcp|fastapi|pydantic"
uname -a

# Error logs
tail -50 logs/errors.log
tail -50 logs/inbox-zen.log

# System status
python -c "
from src.storage import get_email_stats
from src.server import server
print('Server version:', server.version)
print('Email stats:', get_email_stats())
"

# Configuration (redacted)
python -c "
from src.config import config
print('Server name:', config.server_name)
print('Webhook secret configured:', bool(config.postmark_webhook_secret))
print('Server host:', config.server_host)
print('Server port:', config.server_port)
"
```

This troubleshooting guide covers the most common issues and provides systematic approaches to diagnose and resolve problems. For additional help, refer to the logs and use the diagnostic tools provided.
