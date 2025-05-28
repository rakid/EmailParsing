#!/usr/bin/env python3
"""
Simple storage test
"""

print("Starting storage test...")

try:
    # Import the same way as tests
    from src import storage as test_storage
    print("Imported test_storage successfully")
    
    # Import server storage directly
    import sys
    sys.path.append('src')
    import storage as server_storage
    print("Imported server_storage successfully")
    
    print(f"Test storage ID: {id(test_storage.email_storage)}")
    print(f"Server storage ID: {id(server_storage.email_storage)}")
    print(f"Same object? {test_storage.email_storage is server_storage.email_storage}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
