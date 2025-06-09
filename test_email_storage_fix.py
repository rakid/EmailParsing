#!/usr/bin/env python3
"""
Test script to verify email storage and MCP integration
Simulates a Postmark webhook and verifies storage
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

async def test_email_webhook_and_storage():
    """Test complete email processing and storage"""
    print("🧪 Testing email webhook processing and storage...")
    
    try:
        from src.webhook import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Sample Postmark webhook payload
        webhook_payload = {
            "From": "test@example.com",
            "FromName": "Test Sender",
            "To": "support@mycompany.com",
            "ToFull": [{"Email": "support@mycompany.com", "Name": "Support Team"}],
            "Subject": "Test email for MCP storage",
            "MessageID": f"test-message-{datetime.now().timestamp()}",
            "Date": datetime.now(timezone.utc).isoformat(),
            "TextBody": "This is a test email to verify MCP storage functionality.",
            "HtmlBody": "<p>This is a test email to verify MCP storage functionality.</p>",
            "Headers": [
                {"Name": "Content-Type", "Value": "text/html"},
                {"Name": "X-Test", "Value": "MCP-Storage-Test"}
            ],
            "Attachments": [],
            
            # Inbound email fields
            "MailboxHash": "support-test-hash-123",
            "OriginalRecipient": "support@mycompany.com",
            "SpamScore": 0.0,
            "VirusDetected": False,
            "ReplyTo": "test@example.com",
            "Tag": "test-email",
            "MessageStream": "inbound"
        }
        
        print("📤 Sending webhook payload...")
        
        # Send webhook request to test endpoint (no signature verification)
        response = client.post(
            "/webhook/test",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📨 Webhook response: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            processing_id = response_data.get("processing_id")
            print(f"✅ Email processed successfully!")
            print(f"   Processing ID: {processing_id}")
            print(f"   Message: {response_data.get('message')}")
            
            # Check storage immediately after processing
            print("\n🔍 Checking storage status...")
            storage_response = client.get("/debug/storage")
            
            if storage_response.status_code == 200:
                storage_data = storage_response.json()
                total_emails = storage_data["memory_storage"]["total_emails"]
                email_ids = storage_data["memory_storage"]["email_ids"]
                stats = storage_data["memory_storage"]["stats"]
                
                print(f"📊 Storage Status:")
                print(f"   Total emails: {total_emails}")
                print(f"   Email IDs: {email_ids}")
                print(f"   Total processed: {stats['total_processed']}")
                print(f"   Total errors: {stats['total_errors']}")
                
                if total_emails > 0:
                    print("✅ Email successfully stored in memory!")
                    
                    # Check recent emails
                    recent_emails = storage_data["recent_emails"]
                    if recent_emails:
                        latest_email = recent_emails[-1]
                        print(f"\n📧 Latest email details:")
                        print(f"   ID: {latest_email['id']}")
                        print(f"   Subject: {latest_email['subject']}")
                        print(f"   From: {latest_email['from']}")
                        print(f"   Status: {latest_email['status']}")
                        print(f"   Has analysis: {latest_email['has_analysis']}")
                        print(f"   Urgency level: {latest_email['urgency_level']}")
                        print(f"   Inbound address: {latest_email['inbound_email_address']}")
                        
                        return True
                else:
                    print("❌ Email NOT found in storage!")
                    return False
            else:
                print(f"❌ Storage check failed: {storage_response.status_code}")
                return False
        else:
            print(f"❌ Webhook failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mcp_api_access():
    """Test MCP API access to stored emails"""
    print("\n🧪 Testing MCP API access...")
    
    try:
        from src.webhook import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test recent emails endpoint
        response = client.get("/api/emails/recent?limit=5")
        print(f"📊 Recent emails API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Count: {data.get('count', 0)}")
            print(f"   Emails returned: {len(data.get('emails', []))}")
            
            if data.get('emails'):
                for email in data['emails']:
                    print(f"   - {email['subject']} (urgency: {email['urgency_level']})")
                return True
            else:
                print("   No emails found via API")
                return False
        else:
            print(f"   API error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ MCP API test failed: {e}")
        return False

async def test_routing_functionality():
    """Test email routing based on inbound address"""
    print("\n🧪 Testing email routing functionality...")
    
    try:
        from src.webhook import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test routing stats
        response = client.get("/api/routing/stats")
        print(f"📊 Routing stats API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Total rules: {data.get('total_rules', 0)}")
            print(f"   Enabled rules: {data.get('enabled_rules', 0)}")
            
            runtime_stats = data.get('runtime_stats', {})
            print(f"   Emails routed: {runtime_stats.get('emails_routed', 0)}")
            print(f"   Routing rate: {runtime_stats.get('routing_rate', 0):.2%}")
            
            return True
        else:
            print(f"   Routing API error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Routing test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Email Storage and MCP Integration\n")
    
    tests = [
        ("Email Webhook and Storage", test_email_webhook_and_storage),
        ("MCP API Access", test_mcp_api_access),
        ("Routing Functionality", test_routing_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n📊 Test Results Summary:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Email storage and MCP integration working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Email storage may have issues.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
