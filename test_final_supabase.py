#!/usr/bin/env python3
"""
Test Final Supabase - Email vers Supabase
"""

import requests
import json
from datetime import datetime

# Test email payload pour Supabase
test_payload = {
    "MessageID": f"final-supabase-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}@test.com",
    "From": "final-test@example.com",
    "To": "inbox@inzen.email",
    "Subject": "🚀 FINAL SUPABASE TEST - Should appear in Supabase!",
    "TextBody": "This email should now be stored in Supabase database using our ultra-lightweight client!",
    "HtmlBody": "<p>This email should now be stored in <strong>Supabase database</strong> using our ultra-lightweight client!</p>",
    "Date": datetime.now().isoformat(),
    "ToFull": [{"Email": "inbox@inzen.email", "Name": "Inbox Zen"}],
    "CcFull": [],
    "BccFull": [],
    "Attachments": [],
    "Headers": [
        {"Name": "X-Test-Type", "Value": "Final-Supabase-Test"},
        {"Name": "X-Test-Timestamp", "Value": datetime.now().isoformat()}
    ],
    "MailboxHash": "inbox@inzen.email",
    "OriginalRecipient": "inbox@inzen.email",
    "SpamScore": 0.0,
    "VirusDetected": False,
    "ReplyTo": "final-test@example.com",
    "MessageStream": "inbound",
    "Tag": "final-supabase-test"
}

def main():
    print("🚀 FINAL SUPABASE TEST")
    print("=" * 50)
    
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
            print(f"   1. Supabase Table Editor: Refresh the emails table")
            print(f"   2. You should see the new email with ID: {result.get('processing_id')}")
            print(f"   3. Dashboard: https://inzen.email")
            print(f"   4. Debug endpoint: https://inzen.email/debug/supabase-emails")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    main()
