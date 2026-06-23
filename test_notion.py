#!/usr/bin/env python3
"""
Test script to check Notion API availability and demonstrate what's needed
"""

import os
import json
from datetime import datetime, timedelta

print("=" * 60)
print("KM-SIGNAL-PIPELINE TEST")
print("=" * 60)

# Check for Notion token in environment
notion_token = os.environ.get('NOTION_TOKEN', '')
if notion_token:
    print("✓ NOTION_TOKEN found in environment")
else:
    print("✗ NOTION_TOKEN not found")
    print("\nTo fix this, you need to:")
    print("1. Get your Notion integration token")
    print("2. Export it: export NOTION_TOKEN='your-token-here'")

# Show what the pipeline needs
print("\n" + "=" * 60)
print("REQUIRED INTEGRATIONS:")
print("=" * 60)
print("""
1. NOTION API:
   - Database ID: f22d80836d1d4759a1c0c133a4cce8c9 (MeetingDiary)
   - Database ID: 1a51db9ba44180969722c19633401f15 (DealStrategy)
   - Needs: Query, Read, Update capabilities
   
2. GOOGLE DRIVE API:
   - Needs: File download capability for VTT transcripts
   - File IDs extracted from Notion transcript URLs
   
3. GOOGLE CHAT WEBHOOK:
   - URL: Already configured in skill
   - Mode: TEST_MODE (won't actually post)
""")

print("\n" + "=" * 60)
print("SIMULATED QUERY:")
print("=" * 60)

# Simulate what we would query
yesterday = datetime.now() - timedelta(days=1)
query_date = yesterday.strftime("%Y-%m-%d")

print(f"""
Would query MeetingDiary with:
- Meeting Date: {query_date}
- Status: "Recent Client Meeting"
- Added to Google Chat: false
- Meeting Type in: [CSM Check In, CSM Success Call, Sales Halo Demo, etc.]
- Transcript URL: not empty
""")

print("\n" + "=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print("""
If you have MCP configured in Claude Desktop:
1. Check Developer > MCP Servers in settings
2. Ensure 'notion' and 'gdrive' servers are enabled
3. Restart Claude Desktop if needed
4. The MCP tools should appear as mcp__[id]__[function]

Alternative: Use Python with notion-client library:
pip install notion-client google-api-python-client
""")