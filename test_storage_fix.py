#!/usr/bin/env python3
"""
Test storage fix - using same import pattern as server
"""

print("Testing storage fix...")

try:
    import os
    import sys

    # Add src directory to path (same as server.py)
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
    
    # Import server (which imports storage)
    # Import storage using same pattern as server
    import storage
    from src import server
    
    print(f"Storage ID: {id(storage.email_storage)}")
    print(f"Storage length: {len(storage.email_storage)}")
    
    # Add test data
    from models import EmailData, EmailStatus, ProcessedEmail
    
    email_data = EmailData(
        message_id="test-fix",
        from_email="test@example.com", 
        to_emails=["recipient@example.com"],
        subject="Test",
        text_body="Test"
    )
    
    processed_email = ProcessedEmail(
        id="test-fix",
        email_data=email_data,
        status=EmailStatus.PROCESSED
    )
    
    storage.email_storage["test-fix"] = processed_email
    print(f"After adding: {len(storage.email_storage)}")
    
    # Test server access
    import asyncio
    async def test_server():
        result = await server.handle_read_resource("email://processed")
        import json
        data = json.loads(result.contents[0].text)
        return data["total_count"]
    
    count = asyncio.run(test_server())
    print(f"Server sees count: {count}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
