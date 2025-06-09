#!/usr/bin/env python3
"""
Test script for the new /health/services endpoint
Tests both webhook and MCP API versions
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

async def test_webhook_health_services():
    """Test the webhook /health/services endpoint"""
    print("🧪 Testing Webhook /health/services endpoint...")
    
    try:
        from src.webhook import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health/services")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook health services endpoint working!")
            print(f"Overall Status: {data.get('overall_status')}")
            print(f"Services Checked: {list(data.get('services', {}).keys())}")
            
            # Print service statuses
            for service_name, service_info in data.get('services', {}).items():
                status = service_info.get('status', 'unknown')
                configured = service_info.get('configured', False)
                print(f"  - {service_name}: {status} (configured: {configured})")
            
            # Print missing configurations
            missing = data.get('missing_config', [])
            if missing:
                print(f"Missing Config: {missing}")
            
            # Print warnings
            warnings = data.get('warnings', [])
            if warnings:
                print(f"Warnings: {len(warnings)} warnings")
                for warning in warnings[:3]:  # Show first 3
                    print(f"  - {warning}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception testing webhook: {e}")
        return False

async def test_mcp_health_services():
    """Test the MCP /mcp/health/services endpoint"""
    print("\n🧪 Testing MCP /mcp/health/services endpoint...")
    
    try:
        from api.mcp import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/mcp/health/services")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ MCP health services endpoint working!")
            print(f"Overall Status: {data.get('overall_status')}")
            print(f"MCP Available: {data.get('mcp_available')}")
            print(f"Services Checked: {list(data.get('services', {}).keys())}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception testing MCP: {e}")
        return False

async def test_basic_health():
    """Test basic health endpoints"""
    print("\n🧪 Testing basic health endpoints...")
    
    try:
        from src.webhook import app as webhook_app
        from api.mcp import app as mcp_app
        from fastapi.testclient import TestClient
        
        # Test webhook health
        webhook_client = TestClient(webhook_app)
        webhook_response = webhook_client.get("/health")
        print(f"Webhook /health: {webhook_response.status_code}")
        
        # Test MCP health
        mcp_client = TestClient(mcp_app)
        mcp_response = mcp_client.get("/mcp/health")
        print(f"MCP /mcp/health: {mcp_response.status_code}")
        
        return webhook_response.status_code == 200 and mcp_response.status_code == 200
        
    except Exception as e:
        print(f"❌ Exception testing basic health: {e}")
        return False

def test_environment_detection():
    """Test environment variable detection"""
    print("\n🧪 Testing environment variable detection...")
    
    # Check current environment variables
    env_vars = {
        "SAMBANOVA_API_KEY": os.getenv("SAMBANOVA_API_KEY"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
        "POSTMARK_WEBHOOK_SECRET": os.getenv("POSTMARK_WEBHOOK_SECRET"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
    }
    
    print("Current Environment Variables:")
    for key, value in env_vars.items():
        if value:
            print(f"  ✅ {key}: {'*' * min(len(value), 8)}... (length: {len(value)})")
        else:
            print(f"  ❌ {key}: Not set")
    
    return True

async def main():
    """Run all tests"""
    print("🚀 Testing Health Services Endpoints\n")
    
    # Test environment detection first
    test_environment_detection()
    
    # Test basic health endpoints
    basic_ok = await test_basic_health()
    
    # Test new services health endpoints
    webhook_ok = await test_webhook_health_services()
    mcp_ok = await test_mcp_health_services()
    
    print("\n📊 Test Results Summary:")
    print(f"  Basic Health: {'✅' if basic_ok else '❌'}")
    print(f"  Webhook Services Health: {'✅' if webhook_ok else '❌'}")
    print(f"  MCP Services Health: {'✅' if mcp_ok else '❌'}")
    
    if all([basic_ok, webhook_ok, mcp_ok]):
        print("\n🎉 All tests passed! Health services endpoints are working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
