# Health Services API Documentation

## 🏥 Overview

The Health Services API provides comprehensive monitoring of all external services and configurations used by the Inbox Zen MCP Server. This includes SambaNova AI, Supabase database, Postmark webhooks, and environment configuration.

## 📍 Endpoints

### 1. Basic Health Check

```http
GET /health
GET /mcp/health
```

**Response:**
```json
{
  "status": "healthy",
  "server_name": "Inbox Zen MCP Server",
  "server_version": "1.0.0",
  "timestamp": "2025-01-06T12:00:00Z"
}
```

### 2. Comprehensive Services Health Check

```http
GET /health/services
GET /mcp/health/services
```

**Response Structure:**
```json
{
  "timestamp": "2025-01-06T12:00:00Z",
  "overall_status": "healthy|warning|degraded|error",
  "services": {
    "sambanova": { /* SambaNova AI status */ },
    "supabase": { /* Database status */ },
    "postmark": { /* Webhook status */ }
  },
  "configuration": { /* Environment config */ },
  "missing_config": ["service.VARIABLE_NAME"],
  "warnings": ["service: warning message"],
  "source": "webhook_api|mcp_api"
}
```

## 🤖 SambaNova AI Service

**Status Indicators:**
- ✅ **healthy**: API key configured, plugin available
- ⚠️ **warning**: Plugin available but API key missing
- ❌ **error**: Plugin import failed or unexpected error

**Configuration Required:**
```bash
SAMBANOVA_API_KEY=your_api_key_here
SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct  # Optional
SAMBANOVA_BASE_URL=https://api.sambanova.ai/v1  # Optional
```

**Response Details:**
```json
{
  "name": "SambaNova AI",
  "status": "healthy",
  "configured": true,
  "accessible": true,
  "missing_config": [],
  "warnings": [],
  "details": {
    "api_key_configured": true,
    "api_key_length": 36,
    "model": "Meta-Llama-3.3-70B-Instruct",
    "base_url": "https://api.sambanova.ai/v1",
    "plugin_available": true,
    "plugin_name": "sambanova-ai-analysis",
    "plugin_version": "1.0.0",
    "connectivity_test": "skipped_to_avoid_costs"
  }
}
```

## 💾 Supabase Database Service

**Status Indicators:**
- ✅ **healthy**: URL and keys configured, client initialized
- ⚠️ **warning**: Missing configuration, using in-memory storage
- ❌ **error**: Connection failed or unexpected error

**Configuration Required:**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key  # Optional
```

**Response Details:**
```json
{
  "name": "Supabase Database",
  "status": "warning",
  "configured": false,
  "accessible": false,
  "missing_config": ["SUPABASE_URL", "SUPABASE_ANON_KEY"],
  "warnings": ["Database not configured - using in-memory storage"],
  "details": {
    "url_configured": false,
    "anon_key_configured": false,
    "service_key_configured": false
  }
}
```

## 📧 Postmark Webhook Service

**Status Indicators:**
- ✅ **healthy**: Webhook secret configured, signature verification enabled
- ⚠️ **warning**: No webhook secret, signature verification disabled
- ❌ **error**: Configuration error

**Configuration Required:**
```bash
POSTMARK_WEBHOOK_SECRET=your_webhook_secret
```

**Response Details:**
```json
{
  "name": "Postmark Webhook",
  "status": "healthy",
  "configured": true,
  "accessible": true,
  "missing_config": [],
  "warnings": [],
  "details": {
    "signature_verification": true,
    "secret_length": 19,
    "webhook_endpoint": "/webhook",
    "environment": "production"
  }
}
```

## ⚙️ Environment Configuration

**Included Information:**
```json
{
  "environment": "production",
  "log_level": "INFO",
  "log_format": "json",
  "vercel_deployment": true,
  "deployment_id": "dpl_xyz123",
  "python_path": "./",
  "serverless_optimizations": true,
  "integrations_available": true
}
```

## 🚨 Status Levels

### Overall Status Logic
- **healthy**: All services configured and working
- **warning**: Some services missing configuration but app functional
- **degraded**: Critical services have errors but app partially functional
- **error**: Major system errors preventing normal operation

### Service Status Logic
- **healthy**: Service fully configured and accessible
- **warning**: Service has configuration issues but app can function
- **error**: Service has critical errors

## 🔧 Usage Examples

### Check if SambaNova AI is ready
```bash
curl https://your-app.vercel.app/health/services | jq '.services.sambanova.status'
```

### Get missing configuration
```bash
curl https://your-app.vercel.app/health/services | jq '.missing_config[]'
```

### Monitor overall health
```bash
curl https://your-app.vercel.app/health/services | jq '.overall_status'
```

### Check via MCP API
```bash
curl https://your-app.vercel.app/mcp/health/services | jq '.services'
```

## 🚀 Deployment Monitoring

Use these endpoints for:
- **CI/CD Health Checks**: Verify deployment success
- **Monitoring Dashboards**: Track service availability
- **Debugging**: Identify missing configuration
- **Alerting**: Set up alerts for degraded services

## 📊 Integration with Monitoring Tools

### Prometheus/Grafana
```yaml
# prometheus.yml
- job_name: 'inbox-zen-health'
  static_configs:
    - targets: ['your-app.vercel.app']
  metrics_path: '/health/services'
```

### Uptime Monitoring
- **Endpoint**: `/health/services`
- **Expected Status**: `200`
- **Alert on**: `overall_status != "healthy"`

### Log Aggregation
The health check provides structured JSON perfect for log aggregation tools like ELK stack or Datadog.
