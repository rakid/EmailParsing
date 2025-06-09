# Inbound Email Address Support

## 🎯 Overview

The Inbox Zen MCP Server fully supports Postmark's `inbound_email_address` (MailboxHash) functionality, enabling sophisticated email routing and processing based on the specific email address that received the message.

## 📧 Postmark Integration

### Supported Fields

The application now captures and processes these Postmark inbound email fields:

```json
{
  "MailboxHash": "support-inbox-hash-123",
  "OriginalRecipient": "support@mycompany.com", 
  "SpamScore": 0.1,
  "VirusDetected": false,
  "ReplyTo": "sender@example.com",
  "Tag": "support-emails",
  "MessageStream": "inbound"
}
```

### EmailData Model Enhancement

The `EmailData` model includes these new fields:

```python
class EmailData(BaseModel):
    # ... existing fields ...
    
    # Inbound email routing
    inbound_email_address: Optional[str]  # MailboxHash from Postmark
    original_recipient: Optional[str]     # Original recipient before forwarding
    
    # Email security and quality
    spam_score: Optional[float]           # Spam score from provider
    virus_detected: Optional[bool]        # Virus detection result
    
    # Additional metadata
    reply_to: Optional[str]               # Reply-To header
    message_stream: Optional[str]         # Postmark message stream
    tag: Optional[str]                    # Postmark tag
```

## 🔀 Email Routing System

### Automatic Routing

Emails are automatically routed based on their `inbound_email_address`:

```python
# Example routing logic
if email.inbound_email_address == "support-hash":
    # Route to support team with high priority
    email.headers["X-Priority"] = "high"
    email.headers["X-Forward-To-Team"] = "support"
```

### Default Routing Rules

| Inbound Address Pattern | Action | Team | Priority |
|------------------------|--------|------|----------|
| `support`, `help`, `contact` | Process Priority | Support | 100 |
| `sales`, `info`, `hello` | Forward to Team | Sales | 90 |
| `billing`, `invoices`, `payments` | Forward to Team | Finance | 80 |
| `noreply`, `no-reply`, `donotreply` | Archive | None | 70 |

### Custom Routing Rules

Add custom routing rules programmatically:

```python
from src.email_routing import email_router, RoutingRule, RoutingAction

# Add custom rule
custom_rule = RoutingRule(
    name="vip_customers",
    description="Route VIP customer emails to priority queue",
    inbound_addresses=["vip", "premium", "enterprise"],
    action=RoutingAction.PROCESS_PRIORITY,
    priority=150,
    metadata={"team": "vip_support", "sla_hours": 1}
)

email_router.add_rule(custom_rule)
```

### Pattern Matching

The routing system supports multiple pattern types:

```python
# Exact match
inbound_addresses=["support"]

# Contains match  
inbound_addresses=["support-"]  # Matches "support-team", "support-billing"

# Regex match
inbound_addresses=["regex:^(help|support)-.*"]  # Matches "help-billing", "support-tech"
```

## 🛠️ API Endpoints

### Get Routing Statistics

```http
GET /api/routing/stats
```

**Response:**
```json
{
  "total_rules": 4,
  "enabled_rules": 4,
  "custom_handlers": 0,
  "runtime_stats": {
    "total_emails_processed": 25,
    "emails_routed": 18,
    "routing_rate": 0.72,
    "inbound_addresses_seen": 5
  },
  "rules": [...]
}
```

### Get Routing Rules

```http
GET /api/routing/rules
```

**Response:**
```json
{
  "rules": [
    {
      "name": "support_emails",
      "description": "Route support emails to priority processing",
      "inbound_addresses": ["support", "help", "contact"],
      "action": "process_priority",
      "priority": 100,
      "enabled": true,
      "metadata": {"team": "support", "sla_hours": 4}
    }
  ]
}
```

### Get Emails by Inbound Address

```http
GET /api/emails/by-inbound-address?inbound_address=support-hash&limit=10
```

**Response:**
```json
{
  "filter": "support-hash",
  "total_found": 5,
  "returned": 5,
  "available_inbound_addresses": ["support-hash", "sales-hash", "billing-hash"],
  "emails": [
    {
      "id": "email-123",
      "subject": "Need technical help",
      "from": "customer@example.com",
      "inbound_email_address": "support-hash",
      "original_recipient": "support@mycompany.com",
      "routing_rule": "support_emails",
      "routing_action": "process_priority",
      "urgency_level": "high",
      "sentiment": "neutral"
    }
  ]
}
```

## 🔧 Configuration

### Postmark Setup

1. **Configure Inbound Domain:**
   ```
   Set up inbound processing in Postmark dashboard
   Configure webhook URL: https://your-app.vercel.app/webhook
   ```

2. **Enable Required Fields:**
   ```
   ✅ Include raw email content (optional)
   ✅ Include spam score
   ✅ Include virus detection
   ✅ Include original recipient
   ```

### Environment Variables

```bash
# Postmark configuration
POSTMARK_WEBHOOK_SECRET=your_webhook_secret

# Optional: Enable advanced routing
EMAIL_ROUTING_ENABLED=true
EMAIL_ROUTING_LOG_LEVEL=INFO
```

## 📊 Monitoring and Analytics

### Routing Metrics

Monitor routing effectiveness:

```bash
# Check routing statistics
curl https://your-app.vercel.app/api/routing/stats | jq '.runtime_stats'

# View routing rules
curl https://your-app.vercel.app/api/routing/rules | jq '.rules[].name'

# Get emails by specific inbound address
curl "https://your-app.vercel.app/api/emails/by-inbound-address?inbound_address=support-hash"
```

### Health Check Integration

The routing system is included in health checks:

```bash
curl https://your-app.vercel.app/health/services | jq '.services.postmark.details'
```

## 🎯 Use Cases

### 1. Department Routing

```python
# Route emails to different departments
support_rule = RoutingRule(
    name="support_routing",
    inbound_addresses=["support", "help", "technical"],
    action=RoutingAction.FORWARD_TO_TEAM,
    metadata={"team": "support", "slack_channel": "#support"}
)
```

### 2. Priority Processing

```python
# VIP customer priority
vip_rule = RoutingRule(
    name="vip_priority",
    inbound_addresses=["vip", "enterprise"],
    action=RoutingAction.PROCESS_PRIORITY,
    metadata={"sla_hours": 1, "escalate": True}
)
```

### 3. Automated Archiving

```python
# Archive automated emails
archive_rule = RoutingRule(
    name="auto_archive",
    inbound_addresses=["noreply", "automated"],
    action=RoutingAction.ARCHIVE,
    metadata={"auto_archive": True}
)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test inbound email address support
python test_inbound_email_support.py

# Expected output:
# 🎉 All inbound email address tests passed!
```

## 🔍 Troubleshooting

### Common Issues

1. **MailboxHash not captured:**
   - Verify Postmark webhook includes all fields
   - Check webhook payload in logs

2. **Routing not working:**
   - Verify routing rules are enabled
   - Check pattern matching logic
   - Review routing logs

3. **API endpoints returning 404:**
   - Ensure email routing module is imported
   - Check API routes are loaded

### Debug Commands

```bash
# Check if routing is working
curl https://your-app.vercel.app/api/routing/stats

# View recent emails with routing info
curl https://your-app.vercel.app/api/emails/recent | jq '.emails[].routing_rule'

# Test specific inbound address
curl "https://your-app.vercel.app/api/emails/by-inbound-address?inbound_address=your-hash"
```

## 🎉 Summary

✅ **Full Postmark Integration**: Complete support for MailboxHash and inbound fields  
✅ **Intelligent Routing**: Automatic email routing based on inbound address  
✅ **Flexible Rules**: Custom routing rules with priority and metadata  
✅ **API Access**: REST endpoints for routing management and analytics  
✅ **Monitoring**: Health checks and routing statistics  
✅ **Production Ready**: Tested and deployed on Vercel

The inbound email address support enables sophisticated email processing workflows, making it easy to route emails to appropriate teams, set priorities, and automate responses based on the receiving email address.
