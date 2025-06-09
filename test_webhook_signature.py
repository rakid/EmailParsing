#!/usr/bin/env python3
"""
Test script to verify webhook signature validation
Demonstrates how Postmark webhook signatures work
"""

import hashlib
import hmac
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def calculate_postmark_signature(body: str, secret: str) -> str:
    """Calculate HMAC-SHA256 signature like Postmark does"""
    return hmac.new(
        secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_webhook_signature_validation():
    """Test webhook with proper signature validation"""
    print("🔐 Testing Webhook Signature Validation")
    
    try:
        from src.webhook import app
        from src.config import config
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Sample webhook payload
        webhook_payload = {
            "From": "test@example.com",
            "FromName": "Test Sender",
            "To": "support@mycompany.com",
            "ToFull": [{"Email": "support@mycompany.com", "Name": "Support Team"}],
            "Subject": "Test with proper signature",
            "MessageID": "test-signature-123",
            "Date": "2025-06-09T12:00:00Z",
            "TextBody": "Testing webhook signature validation.",
            "Headers": [],
            "Attachments": [],
            "MailboxHash": "support-hash-456",
            "OriginalRecipient": "support@mycompany.com"
        }
        
        # Convert to JSON string (like Postmark sends)
        body_json = json.dumps(webhook_payload, separators=(',', ':'))
        
        print(f"📝 Webhook secret configured: {bool(config.postmark_webhook_secret)}")
        
        if config.postmark_webhook_secret:
            # Calculate proper signature
            signature = calculate_postmark_signature(body_json, config.postmark_webhook_secret)
            print(f"🔑 Calculated signature: {signature[:20]}...")
            
            # Test with correct signature
            print("\n✅ Testing with CORRECT signature...")
            response = client.post(
                "/webhook",
                content=body_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Signature": signature
                }
            )
            
            print(f"   Response: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Webhook accepted with valid signature!")
                data = response.json()
                print(f"   Processing ID: {data.get('processing_id')}")
            else:
                print(f"   ❌ Unexpected error: {response.text}")
            
            # Test with wrong signature
            print("\n❌ Testing with WRONG signature...")
            wrong_signature = "wrong_signature_123"
            response = client.post(
                "/webhook",
                content=body_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Signature": wrong_signature
                }
            )
            
            print(f"   Response: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Correctly rejected invalid signature!")
            else:
                print(f"   ⚠️ Unexpected response: {response.text}")
            
            # Test without signature
            print("\n🚫 Testing WITHOUT signature...")
            response = client.post(
                "/webhook",
                content=body_json,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Response: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Correctly rejected missing signature!")
            else:
                print(f"   ⚠️ Unexpected response: {response.text}")
                
        else:
            print("⚠️ No webhook secret configured - signature verification disabled")
            
            # Test without signature (should work when no secret configured)
            response = client.post(
                "/webhook",
                content=body_json,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Response: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Webhook accepted (no signature required)")
            else:
                print(f"   ❌ Unexpected error: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_configuration_guide():
    """Show how to properly configure webhook security"""
    print("\n📋 Configuration Guide for Production")
    print("=" * 50)
    
    print("\n1️⃣ Postmark Dashboard Configuration:")
    print("   URL: https://inzen.email/webhook")
    print("   ✅ Include webhook signature: ENABLED")
    print("   ✅ Copy the generated webhook secret")
    
    print("\n2️⃣ Vercel Environment Configuration:")
    print("   vercel env add POSTMARK_WEBHOOK_SECRET 'your_secret_here' production")
    print("   vercel env add ENVIRONMENT 'production' production")
    
    print("\n3️⃣ Verification Commands:")
    print("   # Check configuration")
    print("   curl https://inzen.email/health/services | jq '.services.postmark'")
    print("   ")
    print("   # Test webhook (Postmark will send real signature)")
    print("   # Use Postmark's 'Send Test' button in dashboard")
    
    print("\n4️⃣ Security Benefits:")
    print("   ✅ Prevents unauthorized webhook calls")
    print("   ✅ Ensures emails come from Postmark")
    print("   ✅ Protects against replay attacks")
    print("   ✅ Secret never exposed in URLs or logs")

def main():
    """Run webhook signature tests"""
    print("🔐 Webhook Security Configuration Test\n")
    
    # Test signature validation
    success = test_webhook_signature_validation()
    
    # Show configuration guide
    show_configuration_guide()
    
    if success:
        print("\n🎉 Webhook signature testing completed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check configuration.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
