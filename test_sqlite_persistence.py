#!/usr/bin/env python3
"""
Test SQLite Persistence for Email Storage
"""

import asyncio
import json
import requests
from datetime import datetime

# Test email payload
test_payload = {
    "MessageID": f"test-sqlite-{datetime.now().strftime('%Y%m%d-%H%M%S')}@test.com",
    "From": "test@example.com",
    "To": "inbox@inzen.email",
    "Subject": "🔧 SQLite Persistence Test",
    "TextBody": "This email tests SQLite persistence. It should be saved to the database and remain accessible after serverless function restarts.",
    "HtmlBody": "<p>This email tests <strong>SQLite persistence</strong>. It should be saved to the database and remain accessible after serverless function restarts.</p>",
    "Date": datetime.now().isoformat(),
    "ToFull": [{"Email": "inbox@inzen.email", "Name": "Inbox Zen"}],
    "CcFull": [],
    "BccFull": [],
    "Attachments": [],
    "Headers": [
        {"Name": "X-Test-Type", "Value": "SQLite-Persistence"},
        {"Name": "X-Test-Timestamp", "Value": datetime.now().isoformat()}
    ],
    "MailboxHash": "inbox@inzen.email",
    "OriginalRecipient": "inbox@inzen.email",
    "SpamScore": 0.0,
    "VirusDetected": False,
    "ReplyTo": "test@example.com",
    "MessageStream": "inbound",
    "Tag": "sqlite-test"
}

def test_email_processing():
    """Send test email to webhook endpoint."""
    print("🧪 Testing SQLite Persistence...")
    print(f"📧 Sending test email: {test_payload['Subject']}")
    
    try:
        # Send to webhook endpoint
        response = requests.post(
            "https://inzen.email/webhook",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Email processed successfully!")
            print(f"   Processing ID: {result.get('processing_id')}")
            print(f"   Message: {result.get('message')}")
            return result.get('processing_id')
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def check_storage_status():
    """Check current storage status."""
    print("\n🔍 Checking storage status...")
    
    try:
        # Check memory storage
        response = requests.get("https://inzen.email/debug/storage", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Memory Storage:")
            print(f"   Total emails: {data['memory_storage']['total_emails']}")
            print(f"   Email IDs: {data['memory_storage']['email_ids']}")
        
        # Check API access
        response = requests.get("https://inzen.email/api/emails/recent", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 API Access:")
            print(f"   Count: {data.get('count', 0)}")
            if data.get('emails'):
                for email in data['emails']:
                    print(f"   - {email['subject']} (ID: {email['id']})")
        
    except Exception as e:
        print(f"❌ Storage check failed: {e}")

def main():
    """Main test function."""
    print("🚀 SQLite Persistence Test")
    print("=" * 50)
    
    # Step 1: Send test email
    processing_id = test_email_processing()
    
    if processing_id:
        print(f"\n⏳ Waiting 5 seconds for processing...")
        import time
        time.sleep(5)
        
        # Step 2: Check storage
        check_storage_status()
        
        print(f"\n📝 Test Summary:")
        print(f"   - Email sent with processing ID: {processing_id}")
        print(f"   - Check the dashboard at: https://inzen.email")
        print(f"   - If SQLite works, the email should persist across restarts")
        
    else:
        print("\n❌ Test failed - email was not processed")

if __name__ == "__main__":
    main()
