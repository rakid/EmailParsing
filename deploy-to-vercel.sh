#!/bin/bash

# Vercel Deployment Script for Inbox Zen MCP Server
# This script helps you deploy your MCP server to Vercel with proper configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    print_error "Vercel CLI is not installed. Installing..."
    npm install -g vercel
    print_success "Vercel CLI installed successfully!"
fi

# Check if we're in the right directory
if [ ! -f "vercel.json" ]; then
    print_error "vercel.json not found. Please run this script from the project root directory."
    exit 1
fi

print_status "🚀 Starting Vercel deployment for Inbox Zen MCP Server..."

# Check if .env.vercel exists and offer to copy it
if [ -f ".env.vercel" ] && [ ! -f ".env" ]; then
    read -p "Copy .env.vercel to .env for local configuration? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.vercel .env
        print_success "Environment file copied. Please edit .env with your actual values."
    fi
fi

# Offer to run tests before deployment
read -p "Run tests before deployment? (recommended) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Running tests..."
    if python -m pytest tests/ -v --tb=short; then
        print_success "All tests passed!"
    else
        print_error "Tests failed. Do you want to continue with deployment anyway? (y/n)"
        read -p "" -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Deployment cancelled."
            exit 1
        fi
    fi
fi

# Deploy to Vercel
print_status "Deploying to Vercel..."
if vercel --prod; then
    print_success "Deployment completed successfully!"
else
    print_error "Deployment failed. Please check the output above."
    exit 1
fi

# Get deployment URL
DEPLOYMENT_URL=$(vercel ls | grep "$(basename "$PWD")" | head -1 | awk '{print $2}')

if [ ! -z "$DEPLOYMENT_URL" ]; then
    print_success "Your app is deployed at: https://$DEPLOYMENT_URL"
    
    # Offer to test the deployment
    read -p "Test the deployment? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Testing deployment..."
        
        if command -v python3 &> /dev/null; then
            python3 test_vercel_deployment.py "https://$DEPLOYMENT_URL"
        else
            python test_vercel_deployment.py "https://$DEPLOYMENT_URL"
        fi
    fi
    
    # Show next steps
    echo
    print_status "🎉 Deployment complete! Next steps:"
    echo "1. Configure your Postmark webhook URL: https://$DEPLOYMENT_URL/webhook"
    echo "2. Set environment variables in Vercel dashboard if not already done"
    echo "3. Test your webhook with a sample email"
    echo "4. Monitor your deployment in the Vercel dashboard"
    echo
    print_status "Useful URLs:"
    echo "   - Health check: https://$DEPLOYMENT_URL/health"
    echo "   - MCP health: https://$DEPLOYMENT_URL/mcp/health"
    echo "   - Email stats: https://$DEPLOYMENT_URL/mcp/emails/stats"
    echo "   - Webhook endpoint: https://$DEPLOYMENT_URL/webhook"
    
else
    print_warning "Could not determine deployment URL. Check Vercel dashboard for details."
fi

print_success "Deployment script completed!"
