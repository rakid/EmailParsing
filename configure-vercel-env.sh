#!/bin/bash

# Configure Vercel Environment Variables for Inbox Zen MCP Server
# This script helps set up all required environment variables for optimal functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_status "🔧 Configuring Vercel Environment Variables for Inbox Zen MCP Server"
echo

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    print_error "❌ Vercel CLI not found. Please install it first:"
    echo "npm install -g vercel"
    exit 1
fi

print_status "📋 Based on your health check, these variables need configuration:"
echo

# SambaNova AI Configuration
print_status "🤖 SambaNova AI Configuration"
echo "Status: Currently missing API key and dependencies"
echo

read -p "Do you have a SambaNova API key? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your SambaNova API key: " SAMBANOVA_API_KEY
    if [ ! -z "$SAMBANOVA_API_KEY" ]; then
        vercel env add SAMBANOVA_API_KEY "$SAMBANOVA_API_KEY" production
        print_success "✅ SAMBANOVA_API_KEY configured"
    fi
    
    # Optional: Configure model
    read -p "Enter SambaNova model (default: Meta-Llama-3.3-70B-Instruct): " SAMBANOVA_MODEL
    SAMBANOVA_MODEL=${SAMBANOVA_MODEL:-"Meta-Llama-3.3-70B-Instruct"}
    vercel env add SAMBANOVA_MODEL "$SAMBANOVA_MODEL" production
    print_success "✅ SAMBANOVA_MODEL configured: $SAMBANOVA_MODEL"
else
    print_warning "⚠️ SambaNova AI features will be disabled without API key"
    print_status "You can get an API key from: https://cloud.sambanova.ai/"
fi

echo

# Supabase Configuration
print_status "💾 Supabase Database Configuration"
echo "Status: Variables configured but client library needs to be installed"
echo

read -p "Do you want to configure Supabase for persistent storage? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your Supabase URL: " SUPABASE_URL
    if [ ! -z "$SUPABASE_URL" ]; then
        vercel env add SUPABASE_URL "$SUPABASE_URL" production
        print_success "✅ SUPABASE_URL configured"
    fi
    
    read -p "Enter your Supabase Anon Key: " SUPABASE_ANON_KEY
    if [ ! -z "$SUPABASE_ANON_KEY" ]; then
        vercel env add SUPABASE_ANON_KEY "$SUPABASE_ANON_KEY" production
        print_success "✅ SUPABASE_ANON_KEY configured"
    fi
    
    read -p "Enter your Supabase Service Role Key (optional): " SUPABASE_SERVICE_ROLE_KEY
    if [ ! -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
        vercel env add SUPABASE_SERVICE_ROLE_KEY "$SUPABASE_SERVICE_ROLE_KEY" production
        print_success "✅ SUPABASE_SERVICE_ROLE_KEY configured"
    fi
else
    print_warning "⚠️ Using in-memory storage (data will not persist between deployments)"
fi

echo

# Postmark Configuration
print_status "📧 Postmark Webhook Configuration"
echo "Status: Missing webhook secret (security risk)"
echo

read -p "Enter your Postmark Webhook Secret: " POSTMARK_WEBHOOK_SECRET
if [ ! -z "$POSTMARK_WEBHOOK_SECRET" ]; then
    vercel env add POSTMARK_WEBHOOK_SECRET "$POSTMARK_WEBHOOK_SECRET" production
    print_success "✅ POSTMARK_WEBHOOK_SECRET configured"
    print_success "✅ Webhook signature verification will be enabled"
else
    print_warning "⚠️ Webhook signature verification will be disabled (security risk)"
fi

echo

# Environment Configuration
print_status "⚙️ Environment Configuration"
vercel env add ENVIRONMENT "production" production
vercel env add LOG_LEVEL "INFO" production
vercel env add LOG_FORMAT "json" production
print_success "✅ Environment variables configured"

echo

# Summary
print_status "📊 Configuration Summary"
echo
print_success "✅ Environment variables have been configured in Vercel"
print_status "🚀 Next steps:"
echo "1. Redeploy your application: vercel --prod"
echo "2. Test the health endpoint: curl https://your-app.vercel.app/health/services"
echo "3. Verify all services show 'healthy' status"
echo "4. Configure your Postmark webhook URL to point to your deployment"

echo
print_status "🔗 Useful commands after deployment:"
echo "vercel env ls                    # List all environment variables"
echo "vercel logs                      # View deployment logs"
echo "curl https://your-app.vercel.app/health/services | jq '.overall_status'"

echo
print_success "🎉 Configuration completed!"
