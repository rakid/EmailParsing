# Security and Authentication Guide

## Inbox Zen Email Parsing MCP Server Security

This document outlines the security considerations, authentication methods, and best practices for deploying and using the Inbox Zen Email Parsing MCP Server.

---

## Current Security Status

### Development Mode (Current)

- ⚠️ **No Authentication Required**
- ⚠️ **Open Access to All Resources**
- ⚠️ **No Rate Limiting**
- ⚠️ **Debug Mode Enabled**
- ✅ **Input Validation Active**
- ✅ **Error Handling Secure**

### Recommended for Production

- ✅ **API Key Authentication**
- ✅ **Role-Based Access Control**
- ✅ **Rate Limiting and Throttling**
- ✅ **Audit Logging**
- ✅ **HTTPS/TLS Encryption**
- ✅ **Input Sanitization**

---

## Authentication Methods

### 1. API Key Authentication (Recommended)

#### Implementation

```python
# Environment variable configuration
API_KEY_REQUIRED=true
VALID_API_KEYS=key1,key2,key3

# Header-based authentication
headers = {
    "Authorization": "Bearer your-api-key-here",
    "Content-Type": "application/json"
}
```

#### MCP Client Configuration

```python
# In MCP client connection
server_params = StdioServerParameters(
    command="python",
    args=["-m", "src.server"],
    cwd="/path/to/EmailParsing",
    env={
        "PYTHONPATH": "/path/to/EmailParsing",
        "API_KEY": "your-api-key-here"
    }
)
```

#### REST API Usage

```bash
# Health check with API key
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/health

# Get email statistics
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/api/stats
```

### 2. OAuth 2.0 Integration (Future)

#### Planned Implementation

- OAuth 2.0 Bearer Token support
- Integration with popular providers (Google, Microsoft)
- Scope-based access control
- Token refresh capabilities

### 3. Mutual TLS (mTLS) Authentication

#### For High-Security Environments

- Client certificate authentication
- Server certificate validation
- End-to-end encryption
- Identity verification at transport layer

---

## Access Control

### Role-Based Access Control (RBAC)

#### Defined Roles

1. **Admin**

   - Full access to all resources and tools
   - Server configuration and management
   - User management capabilities

2. **Analyst**

   - Read access to all email resources
   - Full access to analysis tools
   - Limited access to statistics

3. **Viewer**

   - Read-only access to processed emails
   - Basic statistics access
   - No analysis tool access

4. **Monitor**
   - Health check access only
   - Basic system statistics
   - No email data access

#### Permission Matrix

| Resource/Tool          | Admin | Analyst | Viewer | Monitor |
| ---------------------- | ----- | ------- | ------ | ------- |
| `email://processed`    | ✅    | ✅      | ✅     | ❌      |
| `email://stats`        | ✅    | ✅      | ✅     | ✅      |
| `email://analytics`    | ✅    | ✅      | ❌     | ❌      |
| `email://high-urgency` | ✅    | ✅      | ✅     | ❌      |
| `analyze_email`        | ✅    | ✅      | ❌     | ❌      |
| `search_emails`        | ✅    | ✅      | ❌     | ❌      |
| Health endpoints       | ✅    | ✅      | ✅     | ✅      |

### Implementation Example

```python
# Role-based access decorator
@require_role("analyst")
async def analyze_email_tool(email_id: str):
    # Tool implementation
    pass

@require_role("viewer")
async def get_processed_emails():
    # Resource implementation
    pass
```

---

## Rate Limiting and Throttling

### Recommended Limits

#### Per API Key (Production)

- **Resource Access:** 100 requests/minute
- **Tool Execution:** 20 requests/minute
- **Search Operations:** 10 requests/minute
- **Webhook Processing:** No limit (trusted source)

#### Per IP Address (Development)

- **All Endpoints:** 200 requests/minute
- **Burst Capacity:** 50 requests in 10 seconds

### Implementation

```python
from functools import wraps
import time
from collections import defaultdict

# Simple rate limiter
rate_limits = defaultdict(list)

def rate_limit(max_requests: int, window_seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            client_id = get_client_id(request)
            now = time.time()

            # Clean old requests
            rate_limits[client_id] = [
                req_time for req_time in rate_limits[client_id]
                if now - req_time < window_seconds
            ]

            if len(rate_limits[client_id]) >= max_requests:
                raise RateLimitExceeded()

            rate_limits[client_id].append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## Input Validation and Sanitization

### Current Validation

#### Email Data Validation

```python
def validate_email_content(content: str) -> str:
    """Sanitize email content"""
    # Remove potentially dangerous patterns
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)

    # Limit content length
    if len(content) > 1_000_000:  # 1MB limit
        content = content[:1_000_000] + "... [truncated]"

    return content
```

#### Parameter Validation

```python
from pydantic import BaseModel, validator

class SearchParams(BaseModel):
    query: str
    limit: int = 10
    urgency_filter: Optional[str] = None

    @validator('query')
    def validate_query(cls, v):
        if len(v) < 1 or len(v) > 1000:
            raise ValueError('Query must be 1-1000 characters')
        # Remove potential injection patterns
        dangerous_patterns = ['<script', 'javascript:', 'on\w+\s*=']
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Query contains potentially dangerous content')
        return v

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v
```

---

## Webhook Security

### Postmark Webhook Validation

#### Signature Verification

```python
import hmac
import hashlib

def verify_postmark_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Postmark webhook signature"""
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)

# Usage in webhook handler
@app.post("/webhooks/postmark")
async def postmark_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get('X-Postmark-Signature')

    if not verify_postmark_signature(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process webhook
    return await process_email_webhook(payload)
```

### IP Allowlisting

```python
ALLOWED_IPS = [
    "3.134.147.250",    # Postmark IPs
    "50.31.156.6",
    "50.31.156.77",
    "18.217.206.57"
]

def verify_source_ip(client_ip: str) -> bool:
    """Verify request comes from allowed IP"""
    return client_ip in ALLOWED_IPS
```

---

## Data Security

### Encryption at Rest

#### Email Content Encryption

```python
from cryptography.fernet import Fernet

class EmailEncryption:
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt_content(self, content: str) -> str:
        """Encrypt email content"""
        encrypted = self.cipher.encrypt(content.encode())
        return encrypted.decode()

    def decrypt_content(self, encrypted_content: str) -> str:
        """Decrypt email content"""
        decrypted = self.cipher.decrypt(encrypted_content.encode())
        return decrypted.decode()
```

### PII Data Handling

#### Sensitive Data Detection

```python
import re

def detect_pii(content: str) -> dict:
    """Detect potentially sensitive information"""
    patterns = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    }

    detected = {}
    for pii_type, pattern in patterns.items():
        matches = re.findall(pattern, content)
        if matches:
            detected[pii_type] = len(matches)

    return detected

def redact_pii(content: str) -> str:
    """Redact sensitive information"""
    # Replace SSNs
    content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', content)
    # Replace credit cards
    content = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                     'XXXX-XXXX-XXXX-XXXX', content)
    return content
```

---

## Logging and Monitoring

### Security Event Logging

#### Audit Log Format

```python
import logging
import json
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type: str, user_id: str = None,
                      ip_address: str = None, details: dict = None):
    """Log security-related events"""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        'details': details or {}
    }

    security_logger.info(json.dumps(event))

# Usage examples
log_security_event('authentication_success', user_id='user123', ip_address='192.168.1.1')
log_security_event('rate_limit_exceeded', ip_address='192.168.1.100')
log_security_event('invalid_api_key', ip_address='192.168.1.200')
```

### Monitoring Alerts

#### Key Metrics to Monitor

- Failed authentication attempts
- Rate limit violations
- Unusual access patterns
- Large data exports
- Error rate spikes
- Resource usage anomalies

---

## Production Deployment Security

### Environment Variables

```bash
# Required security variables
export API_KEY_REQUIRED=true
export VALID_API_KEYS="key1,key2,key3"
export WEBHOOK_SECRET="your-webhook-secret"
export ENCRYPTION_KEY="your-encryption-key"
export ENABLE_HTTPS=true
export REQUIRE_TLS=true

# Optional security features
export ENABLE_RATE_LIMITING=true
export MAX_REQUESTS_PER_MINUTE=100
export ENABLE_IP_ALLOWLISTING=false
export ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8"
```

### HTTPS/TLS Configuration

```python
# For production deployment
import ssl

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Run with HTTPS
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.webhook:app",
        host="0.0.0.0",
        port=443,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
```

### Docker Security

```dockerfile
# Security-hardened Dockerfile
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY docs/ ./docs/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Remove unnecessary packages and files
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "src.server"]
```

---

## Security Checklist

### Pre-Production Checklist

- [ ] **Authentication implemented and tested**
- [ ] **API keys generated and distributed securely**
- [ ] **Rate limiting configured and active**
- [ ] **Input validation comprehensive**
- [ ] **Webhook signatures verified**
- [ ] **HTTPS/TLS enabled**
- [ ] **Audit logging configured**
- [ ] **Error messages don't leak sensitive information**
- [ ] **PII detection and redaction active**
- [ ] **Security headers configured**
- [ ] **Dependency vulnerability scan passed**
- [ ] **Penetration testing completed**

### Ongoing Security Tasks

- [ ] **Regular security updates**
- [ ] **Log monitoring and analysis**
- [ ] **API key rotation**
- [ ] **Access review and cleanup**
- [ ] **Security incident response plan**
- [ ] **Backup and recovery procedures**

---

## Incident Response

### Security Incident Types

1. **Unauthorized Access**

   - Immediate API key revocation
   - Source IP blocking
   - Audit log analysis

2. **Data Breach**

   - Immediate service isolation
   - Affected data identification
   - Stakeholder notification

3. **DDoS Attack**

   - Traffic analysis and filtering
   - Rate limiting adjustment
   - CDN/WAF activation

4. **Malicious Payload**
   - Input validation review
   - Affected systems analysis
   - Security patch deployment

### Contact Information

- **Security Team:** security@inboxzen.dev
- **Emergency Contact:** +1-XXX-XXX-XXXX
- **Incident Response:** incidents@inboxzen.dev
