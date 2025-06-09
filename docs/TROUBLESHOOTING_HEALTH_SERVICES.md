# Troubleshooting Health Services

## 🚨 Common Issues and Solutions

Based on your health check results, here are solutions for common configuration issues.

## 🤖 SambaNova AI Issues

### Issue: "No module named 'aiohttp'"
```json
"warnings": ["SambaNova plugin import failed: No module named 'aiohttp'"]
```

**Solution:**
1. Update `api/requirements.txt` to include:
   ```
   aiohttp>=3.8.0
   openai>=1.0.0
   ```
2. Redeploy to Vercel: `vercel --prod`

### Issue: "API key not configured"
```json
"missing_config": ["SAMBANOVA_API_KEY"]
```

**Solution:**
```bash
# Configure API key in Vercel
vercel env add SAMBANOVA_API_KEY your_api_key_here production

# Optional: Configure model
vercel env add SAMBANOVA_MODEL Meta-Llama-3.3-70B-Instruct production
```

**Get API Key:** https://cloud.sambanova.ai/

## 💾 Supabase Issues

### Issue: "Supabase client library not available"
```json
"warnings": ["Supabase client library not available"]
```

**Solution:**
1. Update `api/requirements.txt` to include:
   ```
   supabase>=2.0.0
   postgrest>=0.10.0
   ```
2. Redeploy to Vercel: `vercel --prod`

### Issue: Missing Supabase configuration
```json
"missing_config": ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
```

**Solution:**
```bash
# Configure Supabase in Vercel
vercel env add SUPABASE_URL https://your-project.supabase.co production
vercel env add SUPABASE_ANON_KEY your_anon_key production
vercel env add SUPABASE_SERVICE_ROLE_KEY your_service_key production
```

**Note:** Without Supabase, the app uses in-memory storage (data doesn't persist).

## 📧 Postmark Issues

### Issue: "Webhook signature verification disabled"
```json
"missing_config": ["POSTMARK_WEBHOOK_SECRET"]
```

**Solution:**
```bash
# Configure webhook secret in Vercel
vercel env add POSTMARK_WEBHOOK_SECRET your_webhook_secret production
```

**Security Risk:** Without this secret, webhook signatures aren't verified.

## 🔧 Quick Fix Script

Use our automated configuration script:

```bash
# Run the configuration helper
./configure-vercel-env.sh

# Then redeploy
vercel --prod
```

## 📊 Verification Steps

After fixing issues:

1. **Redeploy:**
   ```bash
   vercel --prod
   ```

2. **Check health:**
   ```bash
   curl https://your-app.vercel.app/health/services | jq '.overall_status'
   ```

3. **Verify specific service:**
   ```bash
   curl https://your-app.vercel.app/health/services | jq '.services.sambanova.status'
   ```

## 🎯 Target Status

After all fixes, you should see:

```json
{
  "overall_status": "healthy",
  "services": {
    "sambanova": {"status": "healthy", "configured": true},
    "supabase": {"status": "healthy", "configured": true},
    "postmark": {"status": "healthy", "configured": true}
  },
  "missing_config": [],
  "warnings": []
}
```

## 🚀 Deployment Dependencies

### Required for Vercel:
```txt
# api/requirements.txt
mcp>=1.0.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic[email]>=2.0.0
python-multipart>=0.0.6
pydantic-settings>=2.0.0
python-dateutil>=2.8.0
aiofiles>=23.0.0

# SambaNova AI
aiohttp>=3.8.0
openai>=1.0.0

# Supabase
supabase>=2.0.0
postgrest>=0.10.0
```

### Environment Variables:
```bash
# Required for security
POSTMARK_WEBHOOK_SECRET=your_secret

# Required for AI features
SAMBANOVA_API_KEY=your_key
SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct

# Required for persistence
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key

# Optional
SUPABASE_SERVICE_ROLE_KEY=your_service_key
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 📞 Support

If issues persist:
1. Check Vercel deployment logs: `vercel logs`
2. Verify environment variables: `vercel env ls`
3. Test locally first: `python -m src.webhook`
4. Check GitHub Issues for similar problems
