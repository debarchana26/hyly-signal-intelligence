#!/usr/bin/env python3
"""Test database query using search method"""

from notion_client import Client
import json

NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
notion = Client(auth=NOTION_TOKEN)

# The database ID without dashes works for retrieve
DB_ID = "f22d80836d1d4759a1c0c133a4cce8c9"

print("Testing database query methods...")
print("=" * 60)

# Method 1: Try using search to find pages in the database
try:
    print("\nMethod 1: Using search with filter...")
    response = notion.search(
        filter={
            "property": "object",
            "value": "page"
        },
        query="",
        page_size=5
    )
    
    print(f"Found {len(response.get('results', []))} pages")
    for page in response.get('results', [])[:2]:
        if 'properties' in page:
            print(f"  - Page ID: {page['id']}")
            # Look for Meeting Date property
            if 'Meeting Date' in page['properties']:
                print(f"    Has Meeting Date property!")
                
except Exception as e:
    print(f"Search failed: {e}")

# Method 2: Try POST request with requests library
print("\n" + "=" * 60)
print("Method 2: Using requests library...")

try:
    import requests
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Query the database
    url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
    
    body = {
        "page_size": 2,
        "filter": {
            "property": "Meeting Date",
            "date": {
                "is_not_empty": True
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=body)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Query successful!")
        print(f"  Found {len(data.get('results', []))} results")
        print(f"  Has more: {data.get('has_more', False)}")
        
        # Show first result
        if data.get('results'):
            page = data['results'][0]
            print(f"\nFirst page properties:")
            for prop_name, prop_value in page.get('properties', {}).items():
                print(f"  - {prop_name}: {prop_value.get('type')}")
                
    else:
        print(f"✗ Query failed: {response.status_code}")
        print(f"  Error: {response.text}")
        
except ImportError:
    print("requests library not installed. Installing...")
    import subprocess
    subprocess.run(["python3", "-m", "pip", "install", "requests", "--quiet", "--user"])
    print("Please run the script again.")
except Exception as e:
    print(f"Error: {e}")