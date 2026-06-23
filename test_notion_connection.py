#!/usr/bin/env python3
"""Test Notion connection and database access"""

from notion_client import Client

# Your Notion token
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"

# Database IDs from the skill doc
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"

print("Testing Notion connection...")
print("=" * 60)

try:
    # Initialize client
    notion = Client(auth=NOTION_TOKEN)
    
    # Try to retrieve database metadata first
    print(f"Attempting to retrieve database: {MEETING_DIARY_DB}")
    
    # Try different formats
    db_formats = [
        MEETING_DIARY_DB,  # Raw
        "f22d8083-6d1d-4759-a1c0-c133a4cce8c9",  # With dashes
        "f22d80836d1d4759a1c0c133a4cce8c9",  # Without dashes
    ]
    
    for db_id in db_formats:
        try:
            print(f"\nTrying format: {db_id}")
            
            # Try to retrieve database info
            response = notion.databases.retrieve(database_id=db_id)
            print(f"✓ Success! Database title: {response.get('title', [{}])[0].get('plain_text', 'Unknown')}")
            
            # Now try to query it
            print("\nAttempting to query database...")
            # Use the proper endpoint format
            query_response = notion.request(
                path=f"/v1/databases/{db_id}/query",
                method="POST",
                body={
                    "page_size": 1  # Just get 1 result to test
                }
            )
            print(f"✓ Query successful! Found {len(query_response.get('results', []))} results")
            print(f"  Has more: {query_response.get('has_more', False)}")
            break
            
        except Exception as e:
            print(f"✗ Failed: {e}")
            
except Exception as e:
    print(f"\n❌ Connection error: {e}")
    print("\nPossible issues:")
    print("1. Token might be invalid or expired")
    print("2. Database ID might be incorrect")
    print("3. Token might not have access to this database")
    print("\nPlease verify:")
    print("- The token is from a Notion integration with access to your workspace")
    print("- The database is shared with the integration")