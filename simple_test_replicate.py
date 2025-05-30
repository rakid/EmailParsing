#!/usr/bin/env python3
"""Simple test to replicate the exact test scenario"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to Python path (exactly like tests do)
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import exactly like test_server.py does
from src import server, storage
from src.models import EmailAnalysis, EmailData, EmailStatus, ProcessedEmail


async def replicate_test():
    print("=== Replicating Test Scenario ===")
    
    # Sample data exactly like conftest.py
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
    
    print(f"1. Initial storage length: {len(storage.email_storage)}")
    
    # Store a test email (exactly like test does)
    email_data = EmailData(**sample_email_data)
    analysis = EmailAnalysis(**sample_analysis_data)
    processed_email = ProcessedEmail(
        id="test-email-1",
        email_data=email_data,
        analysis=analysis,
        status=EmailStatus.ANALYZED
    )
    storage.email_storage["test-email-1"] = processed_email
    
    print(f"2. After adding email, storage length: {len(storage.email_storage)}")
    print(f"3. Storage keys: {list(storage.email_storage.keys())}")
    
    # Check what the server sees
    print(f"4. Server's storage length: {len(server.storage.email_storage)}")
    print(f"5. Server's storage keys: {list(server.storage.email_storage.keys())}")
    print(f"6. Same storage object? {storage.email_storage is server.storage.email_storage}")
    
    # Read the resource (exactly like test does)
    result = await server.handle_read_resource("email://processed")
    
    print(f"7. Result type: {type(result)}")
    if isinstance(result, str):
        try:
            data = json.loads(result)
            print(f"8. Parsed data keys: {list(data.keys())}")
            print(f"9. Total count: {data.get('total_count', 'NOT FOUND')}")
            print(f"10. Emails length: {len(data.get('emails', []))}")
        except Exception as e:
            print(f"8. JSON parse error: {e}")
            print(f"   Raw result (first 200 chars): {result[:200]}")
    
    print("=== End Test ===")

if __name__ == "__main__":
    asyncio.run(replicate_test())
