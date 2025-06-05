# Vercel Deployment Guide for Inbox Zen MCP Server

This guide helps you deploy the Inbox Zen MCP Email Processing Server to Vercel Serverless.

## 🚀 Quick Deployment

### 1. Prerequisites

- Vercel account ([sign up here](https://vercel.com/signup))
- Vercel CLI installed: `npm install -g vercel`
- Git repository with your project

### 2. Deploy to Vercel

```bash
# Clone your repository
git clone git@github.com:rakid/EmailParsing.git
cd EmailParsing

# Deploy to Vercel
vercel

# Follow the prompts:
# ? Set up and deploy "~/EmailParsing"? [Y/n] y
# ? Which scope do you want to deploy to? Your Account
# ? Link to existing project? [y/N] n
# ? What's your project's name? inbox-zen-mcp-server
# ? In which directory is your code located? ./
```

### 3. Configure Environment Variables

In the Vercel dashboard or using CLI:

```bash
# Set your Postmark webhook secret
vercel env add POSTMARK_WEBHOOK_SECRET

# Set environment to production
vercel env add ENVIRONMENT production

# Set log level
vercel env add LOG_LEVEL INFO

# Set log format for structured logging
vercel env add LOG_FORMAT json

# Optional: API keys for authentication
vercel env add API_KEY_REQUIRED true
vercel env add VALID_API_KEYS "key1,key2,key3"
```

### 4. Custom Domain (Optional)

```bash
# Add custom domain
vercel domains add your-domain.com
vercel alias <deployment-url> your-domain.com
```

## 📡 Available Endpoints

Once deployed, your server will be available at:

### Webhook Endpoints

- `POST /webhook` - Postmark webhook receiver
- `GET /health` - Health check

### REST API Endpoints

- `GET /api/emails/recent` - Get recent emails
- `GET /api/stats` - Get processing statistics
- `GET /api/analytics` - Get email analytics
- `GET /api/search` - Search emails

### MCP API Endpoints

- `GET /mcp/health` - MCP server health
- `GET /mcp/resources` - List MCP resources
- `POST /mcp/resources/read` - Read MCP resource
- `GET /mcp/tools` - List MCP tools
- `POST /mcp/tools/call` - Call MCP tool
- `GET /mcp/emails/stats` - Email stats via MCP
- `GET /mcp/emails/recent` - Recent emails via MCP

## 🔧 Configuration

### Environment Variables

| Variable                  | Description                              | Default     | Required                 |
| ------------------------- | ---------------------------------------- | ----------- | ------------------------ |
| `POSTMARK_WEBHOOK_SECRET` | Postmark webhook signature secret        | None        | No\*                     |
| `ENVIRONMENT`             | Environment (development/production)     | development | No                       |
| `LOG_LEVEL`               | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO        | No                       |
| `LOG_FORMAT`              | Log format (text/json)                   | text        | No                       |
| `API_KEY_REQUIRED`        | Require API key for endpoints            | false       | No                       |
| `VALID_API_KEYS`          | Comma-separated API keys                 | None        | If API_KEY_REQUIRED=true |

\*Webhook signature verification is recommended for production

### Postmark Setup

1. In your Postmark account, go to Server Settings → Webhooks
2. Add webhook URL: `https://your-vercel-domain.vercel.app/webhook`
3. Select "Inbound" events
4. Set the secret to match your `POSTMARK_WEBHOOK_SECRET` environment variable

## 🧪 Testing Your Deployment

### Test Health Check

```bash
curl https://your-vercel-domain.vercel.app/health
```

### Test MCP Health

```bash
curl https://your-vercel-domain.vercel.app/mcp/health
```

### Test Webhook (with test payload)

```bash
curl -X POST https://your-vercel-domain.vercel.app/webhook \
  -H "Content-Type: application/json" \
  -H "X-Postmark-Signature: test-signature" \
  -d '{
    "From": "test@example.com",
    "To": "inbox@yourapp.com",
    "Subject": "Test Email",
    "TextBody": "This is a test email with urgent deadline.",
    "MessageID": "test-123",
    "Date": "2025-05-28T10:30:00.000Z",
    "Headers": [],
    "Attachments": []
  }'
```

### Test MCP Tools

```bash
# List available tools
curl https://your-vercel-domain.vercel.app/mcp/tools

# Get email statistics
curl -X POST https://your-vercel-domain.vercel.app/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_email_stats",
    "arguments": {}
  }'
```

## 🔍 Monitoring and Debugging

### Vercel Dashboard

- View deployment logs in Vercel dashboard
- Monitor function invocations and errors
- Check performance metrics

### Logs Access

```bash
# View recent logs
vercel logs

# Follow logs in real-time
vercel logs --follow
```

### Common Issues

1. **Import Errors**: Ensure all dependencies are in `api/requirements.txt`
2. **Cold Starts**: First requests may be slower due to serverless cold starts
3. **Memory Limits**: Vercel has memory limits for serverless functions
4. **Timeout**: Functions timeout after 30-60 seconds (configurable)

## 🔒 Security Considerations

1. **Always set webhook secrets** for production
2. **Use API keys** if exposing sensitive endpoints
3. **Monitor usage** to prevent abuse
4. **Validate all inputs** (already implemented)
5. **Use HTTPS** (Vercel provides this automatically)

## 📊 Performance Optimization

### Serverless Optimization

- Keep function size small
- Minimize cold start time
- Use efficient data structures
- Cache when possible

### Monitoring

- Use Vercel Analytics
- Monitor function execution time
- Track error rates
- Set up alerts for failures

## 🔄 Continuous Deployment

Connect your Git repository to Vercel for automatic deployments:

1. Import your Git repository in Vercel dashboard
2. Configure build settings (should auto-detect)
3. Set environment variables
4. Enable automatic deployments on push

## 🆘 Support

For issues:

1. Check Vercel deployment logs
2. Review function logs in dashboard
3. Test endpoints individually
4. Check environment variable configuration
5. Verify Postmark webhook configuration

## 📚 Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [Postmark Webhook Documentation](https://postmarkapp.com/developer/webhooks)
