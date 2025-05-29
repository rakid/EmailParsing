#!/usr/bin/env python3
"""Debug script to understand storage isolation in test environment"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to Python path (exactly like tests do)
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=== Storage Isolation Debug ===")

# Import in same order as test_server.py
print("1. Importing test modules...")
from src import server, storage
from src.models import EmailAnalysis, EmailData, EmailStatus, ProcessedEmail

print(f"   server module: {server}")
print(f"   storage module: {storage}")
print(f"   server.storage: {getattr(server, 'storage', 'NOT FOUND')}")

# Check if they're the same
print(f"   storage is server.storage: {storage is getattr(server, 'storage', None)}")

# Create test data exactly like the test does
print("\n2. Creating test data...")
sample_email_data = {
    "message_id": "test-message-123@example.com",
    "from_email": "john.doe@example.com",
    "to_emails": ["jane.smith@company.com"], 
    "subject": "URGENT: Project deadline tomorrow - need your input ASAP",
    "text_body": "Test body content",
    "html_body": "<p>Test HTML</p>",
    "cc_emails": [],
    "bcc_emails": [],
    "attachments": [],
    "received_at": datetime(2025, 5, 27, 14, 30, 0)
}

sample_analysis_data = {
    "urgency_score": 75,
    "urgency_level": "high",
    "sentiment": "negative",
    "confidence": 0.85,
    "keywords": ["urgent", "deadline", "ASAP", "stressed", "prioritize"],
    "action_items": [
        "Review the budget proposal by tomorrow 5 PM",
        "Schedule meeting with stakeholders for Friday", 
        "Submit final report to management",
        "Call John at 555-123-4567"
    ],
    "temporal_references": ["tomorrow", "5 PM", "Friday"],
    "tags": ["urgent", "project", "deadline", "budget"]
}

# Clear storage like conftest.py would
print("\n3. Clearing storage...")
storage.email_storage.clear()
print(f"   storage.email_storage length: {len(storage.email_storage)}")

# Also check server's view
if hasattr(server, 'storage'):
    print(f"   server.storage.email_storage length: {len(server.storage.email_storage)}")

# Create models exactly like test does
print("\n4. Creating models...")
email_data = EmailData(**sample_email_data)
analysis = EmailAnalysis(**sample_analysis_data)
processed_email = ProcessedEmail(
    id="test-email-1",
    email_data=email_data,
    analysis=analysis,
    status=EmailStatus.ANALYZED
)

print(f"   ProcessedEmail created: {processed_email.id}")

# Add to storage exactly like test does
print("\n5. Adding to storage...")
storage.email_storage["test-email-1"] = processed_email
print(f"   Added to storage.email_storage")
print(f"   storage.email_storage length: {len(storage.email_storage)}")
print(f"   storage.email_storage keys: {list(storage.email_storage.keys())}")

# Check server's view again
if hasattr(server, 'storage'):
    print(f"   server.storage.email_storage length: {len(server.storage.email_storage)}")
    print(f"   server.storage.email_storage keys: {list(server.storage.email_storage.keys())}")

# Test server function exactly like test does
print("\n6. Testing server function...")
async def test_server_function():
    result = await server.handle_read_resource("email://processed")
    print(f"   Result type: {type(result)}")
    
    if isinstance(result, str):
        try:
            data = json.loads(result)
            print(f"   Total count from server: {data.get('total_count', 'NOT FOUND')}")
            print(f"   Emails array length: {len(data.get('emails', []))}")
            if 'emails' in data and len(data['emails']) > 0:
                print(f"   First email ID: {data['emails'][0].get('id', 'NO ID')}")
            
            # Print the raw data structure
            print(f"   Raw data keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            print(f"   JSON decode error: {e}")
            print(f"   Raw result: {result[:200]}...")
    else:
        print(f"   Non-string result: {result}")

asyncio.run(test_server_function())

print("\n7. Final storage check...")
print(f"   storage.email_storage length: {len(storage.email_storage)}")
if hasattr(server, 'storage'):
    print(f"   server.storage.email_storage length: {len(server.storage.email_storage)}")

print("\n=== End Debug ===")
