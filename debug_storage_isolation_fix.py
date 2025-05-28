#!/usr/bin/env python3
"""
Test storage isolation fix
"""

# Import the same way as tests
from src import storage as test_storage
from src.models import ProcessedEmail, EmailData, EmailStatus

# Import server which should use the same storage
from src import server

# Add an email using test storage
email_data = EmailData(
    message_id="isolation-test",
    from_email="test@example.com",
    to_emails=["recipient@example.com"],
    subject="Test Email",
    text_body="Test content",
    html_body="<p>Test content</p>"
)

processed_email = ProcessedEmail(
    id="isolation-test",
    email_data=email_data,
    status=EmailStatus.PROCESSED,
)

# Add via test storage
test_storage.email_storage["isolation-test"] = processed_email
print(f"Test storage length after adding: {len(test_storage.email_storage)}")
print(f"Test storage keys: {list(test_storage.email_storage.keys())}")

# Check what server storage sees
import sys
sys.path.append('src')
import storage as server_storage

print(f"Server storage length: {len(server_storage.email_storage)}")
print(f"Server storage keys: {list(server_storage.email_storage.keys())}")

# Check if they're the same object
print(f"Same object? {test_storage.email_storage is server_storage.email_storage}")
print(f"Test storage ID: {id(test_storage.email_storage)}")
print(f"Server storage ID: {id(server_storage.email_storage)}")
