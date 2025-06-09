#!/usr/bin/env python3
"""
Test Supabase Email Storage
"""

import requests
import json
from datetime import datetime

# Test email payload for Supabase
test_payload = {
    "MessageID": f"supabase-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}@test.com",
    "From": "supabase-test@example.com",
    "To": "inbox@inzen.email",
    "Subject": "🔥 Supabase Storage Test",
    "TextBody": "This email should be stored in Supabase database. Check your Supabase dashboard to verify!",
    "HtmlBody": "<p>This email should be stored in <strong>Supabase database</strong>. Check your Supabase dashboard to verify!</p>",
    "Date": datetime.now().isoformat(),
    "ToFull": [{"Email": "inbox@inzen.email", "Name": "Inbox Zen"}],
    "CcFull": [],
    "BccFull": [],
    "Attachments": [],
    "Headers": [
        {"Name": "X-Test-Type", "Value": "Supabase-Storage"},
        {"Name": "X-Test-Timestamp", "Value": datetime.now().isoformat()}
    ],
    "MailboxHash": "inbox@inzen.email",
    "OriginalRecipient": "inbox@inzen.email",
    "SpamScore": 0.0,
    "VirusDetected": False,
    "ReplyTo": "supabase-test@example.com",
    "MessageStream": "inbound",
    "Tag": "supabase-test"
}

def main():
    print("🔥 Testing Supabase Email Storage")
    print("=" * 40)
    
    try:
        # Send to webhook endpoint
        print(f"📧 Sending test email: {test_payload['Subject']}")
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
            
            print(f"\n🔍 Now check:")
            print(f"   1. Supabase Dashboard: https://supabase.com/dashboard")
            print(f"   2. Your emails table should have the new entry")
            print(f"   3. Dashboard: https://inzen.email")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    main()
