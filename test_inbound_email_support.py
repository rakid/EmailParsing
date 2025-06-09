#!/usr/bin/env python3
"""
Test script for inbound_email_address support
Tests Postmark MailboxHash handling and email routing
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

async def test_postmark_payload_parsing():
    """Test parsing of Postmark webhook payload with inbound email fields"""
    print("🧪 Testing Postmark payload parsing with inbound email fields...")
    
    try:
        from src.models import PostmarkWebhookPayload
        
        # Sample Postmark webhook payload with inbound email fields
        sample_payload = {
            "From": "sender@example.com",
            "FromName": "John Doe",
            "To": "support@mycompany.com",
            "ToFull": [{"Email": "support@mycompany.com", "Name": "Support Team"}],
            "Subject": "Need help with billing",
            "MessageID": "test-message-123",
            "Date": "2025-01-06T12:00:00Z",
            "TextBody": "I need help with my billing account.",
            "HtmlBody": "<p>I need help with my billing account.</p>",
            "Headers": [
                {"Name": "Content-Type", "Value": "text/html"},
                {"Name": "X-Priority", "Value": "3"}
            ],
            "Attachments": [],
            
            # Inbound email specific fields
            "MailboxHash": "support-inbox-hash-123",
            "OriginalRecipient": "support@mycompany.com",
            "SpamScore": 0.1,
            "VirusDetected": False,
            "ReplyTo": "sender@example.com",
            "Tag": "support-emails",
            "MessageStream": "inbound"
        }
        
        # Parse the payload
        webhook_payload = PostmarkWebhookPayload(**sample_payload)
        
        print("✅ Postmark payload parsed successfully!")
        print(f"  MailboxHash: {webhook_payload.MailboxHash}")
        print(f"  OriginalRecipient: {webhook_payload.OriginalRecipient}")
        print(f"  SpamScore: {webhook_payload.SpamScore}")
        print(f"  VirusDetected: {webhook_payload.VirusDetected}")
        print(f"  inbound_email_address property: {webhook_payload.inbound_email_address}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error parsing Postmark payload: {e}")
        return False

async def test_email_data_extraction():
    """Test extraction of EmailData with inbound email fields"""
    print("\n🧪 Testing EmailData extraction with inbound email fields...")
    
    try:
        from src.models import PostmarkWebhookPayload
        from src.webhook import extract_email_data
        
        # Sample payload
        sample_payload_data = {
            "From": "customer@example.com",
            "FromName": "Jane Customer",
            "To": "billing@mycompany.com",
            "ToFull": [{"Email": "billing@mycompany.com", "Name": "Billing Team"}],
            "Subject": "Invoice question",
            "MessageID": "test-message-456",
            "Date": "2025-01-06T14:30:00Z",
            "TextBody": "I have a question about my latest invoice.",
            "Headers": [],
            "Attachments": [],
            "MailboxHash": "billing-inbox-hash-456",
            "OriginalRecipient": "billing@mycompany.com",
            "SpamScore": 0.05,
            "VirusDetected": False,
            "ReplyTo": "customer@example.com",
            "Tag": "billing",
            "MessageStream": "inbound"
        }
        
        webhook_payload = PostmarkWebhookPayload(**sample_payload_data)
        email_data = extract_email_data(webhook_payload)
        
        print("✅ EmailData extracted successfully!")
        print(f"  inbound_email_address: {email_data.inbound_email_address}")
        print(f"  original_recipient: {email_data.original_recipient}")
        print(f"  spam_score: {email_data.spam_score}")
        print(f"  virus_detected: {email_data.virus_detected}")
        print(f"  reply_to: {email_data.reply_to}")
        print(f"  tag: {email_data.tag}")
        print(f"  message_stream: {email_data.message_stream}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting EmailData: {e}")
        return False

async def test_email_routing():
    """Test email routing based on inbound email address"""
    print("\n🧪 Testing email routing based on inbound email address...")
    
    try:
        from src.models import EmailData
        from src.email_routing import route_email_by_inbound_address
        
        # Create test email data with different inbound addresses
        test_cases = [
            {
                "inbound_address": "support-inbox-hash-123",
                "subject": "Need technical help",
                "expected_action": "process_priority"
            },
            {
                "inbound_address": "sales-inbox-hash-456", 
                "subject": "Interested in your product",
                "expected_action": "forward_to_team"
            },
            {
                "inbound_address": "billing-inbox-hash-789",
                "subject": "Payment question",
                "expected_action": "forward_to_team"
            },
            {
                "inbound_address": "noreply-inbox-hash-000",
                "subject": "Automated notification",
                "expected_action": "archive"
            }
        ]
        
        routing_results = []
        
        for test_case in test_cases:
            email_data = EmailData(
                message_id=f"test-{test_case['inbound_address']}",
                from_email="test@example.com",
                to_emails=["test@mycompany.com"],
                subject=test_case["subject"],
                received_at=datetime.now(timezone.utc),
                inbound_email_address=test_case["inbound_address"]
            )
            
            # Apply routing
            routed_email = await route_email_by_inbound_address(email_data)
            
            routing_action = routed_email.headers.get("X-Routing-Action", "process_normal")
            routing_rule = routed_email.headers.get("X-Routing-Rule", "default")
            
            result = {
                "inbound_address": test_case["inbound_address"],
                "subject": test_case["subject"],
                "routing_rule": routing_rule,
                "routing_action": routing_action,
                "expected_action": test_case["expected_action"],
                "matched": routing_action == test_case["expected_action"]
            }
            
            routing_results.append(result)
            
            status = "✅" if result["matched"] else "⚠️"
            print(f"  {status} {test_case['inbound_address']}: {routing_action} (rule: {routing_rule})")
        
        successful_routes = sum(1 for r in routing_results if r["matched"])
        print(f"\n📊 Routing Results: {successful_routes}/{len(routing_results)} matched expected actions")
        
        return successful_routes == len(routing_results)
        
    except Exception as e:
        print(f"❌ Error testing email routing: {e}")
        return False

async def test_api_endpoints():
    """Test API endpoints for inbound email address functionality"""
    print("\n🧪 Testing API endpoints for inbound email functionality...")
    
    try:
        from src.webhook import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test routing stats endpoint
        response = client.get("/api/routing/stats")
        print(f"  Routing stats endpoint: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"    Total rules: {stats.get('total_rules', 0)}")
            print(f"    Enabled rules: {stats.get('enabled_rules', 0)}")
        
        # Test routing rules endpoint
        response = client.get("/api/routing/rules")
        print(f"  Routing rules endpoint: {response.status_code}")
        
        if response.status_code == 200:
            rules = response.json()
            print(f"    Available rules: {len(rules.get('rules', []))}")
            for rule in rules.get('rules', [])[:3]:  # Show first 3 rules
                print(f"      - {rule['name']}: {rule['action']} (priority: {rule['priority']})")
        
        # Test emails by inbound address endpoint
        response = client.get("/api/emails/by-inbound-address")
        print(f"  Emails by inbound address endpoint: {response.status_code}")
        
        if response.status_code == 200:
            emails = response.json()
            print(f"    Available inbound addresses: {len(emails.get('available_inbound_addresses', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API endpoints: {e}")
        return False

async def main():
    """Run all inbound email address tests"""
    print("🚀 Testing Inbound Email Address Support\n")
    
    tests = [
        ("Postmark Payload Parsing", test_postmark_payload_parsing),
        ("EmailData Extraction", test_email_data_extraction),
        ("Email Routing", test_email_routing),
        ("API Endpoints", test_api_endpoints)
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
        print("🎉 All inbound email address tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
