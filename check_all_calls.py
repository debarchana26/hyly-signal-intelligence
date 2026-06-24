#!/usr/bin/env python3
"""
Check all available calls in MeetingDiary
"""

import requests
from datetime import datetime, timedelta

# Notion API setup
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def check_calls_for_dates():
    """Check for calls on specific dates"""
    dates_to_check = ["2026-06-22", "2026-06-21", "2026-06-20", "2026-06-19", "2026-06-18"]
    
    print("=" * 60)
    print("CHECKING ALL RECENT CALLS IN MEETINGDIARY")
    print("=" * 60)
    
    for date_str in dates_to_check:
        print(f"\n📅 Checking {date_str}:")
        
        # Query without "Added to Google Chat" filter to see ALL calls
        filter_conditions = {
            "and": [
                {
                    "property": "Status",
                    "status": {"equals": "Recent Client Meeting"}
                },
                {
                    "property": "Meeting Date",
                    "date": {"equals": date_str}
                }
            ]
        }
        
        url = f"https://api.notion.com/v1/databases/{MEETING_DIARY_DB}/query"
        body = {
            "filter": filter_conditions,
            "page_size": 100
        }
        
        response = requests.post(url, headers=NOTION_HEADERS, json=body)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results:
                print(f"  Found {len(results)} total calls on this date:")
                
                for page in results:
                    try:
                        # Extract key info
                        props = page.get("properties", {})
                        
                        # Get title
                        title = "Unknown"
                        if "Discovery" in props:
                            title_prop = props["Discovery"]
                            if title_prop.get("title"):
                                title = title_prop["title"][0]["plain_text"]
                        
                        # Get meeting type
                        meeting_type = "Unknown"
                        if "Meeting Type" in props:
                            mt_prop = props["Meeting Type"]
                            if mt_prop.get("select"):
                                meeting_type = mt_prop["select"]["name"]
                        
                        # Check transcript URLs
                        has_new_transcript = False
                        has_old_transcript = False
                        if "[NEW] GDrive Transcript URL" in props:
                            url_prop = props["[NEW] GDrive Transcript URL"]
                            has_new_transcript = bool(url_prop.get("url"))
                        if "GDrive Transcript URL" in props:
                            url_prop = props["GDrive Transcript URL"]
                            has_old_transcript = bool(url_prop.get("url"))
                        
                        # Check if already processed
                        already_processed = False
                        if "Added to Google Chat" in props:
                            checkbox_prop = props["Added to Google Chat"]
                            already_processed = checkbox_prop.get("checkbox", False)
                        
                        # Status
                        status = []
                        if has_new_transcript or has_old_transcript:
                            status.append("✓ Has transcript")
                        else:
                            status.append("✗ No transcript")
                        
                        if already_processed:
                            status.append("Already processed")
                        else:
                            status.append("Not processed")
                        
                        print(f"    - {title}")
                        print(f"      Type: {meeting_type}")
                        print(f"      Status: {' | '.join(status)}")
                        
                    except Exception as e:
                        print(f"    - Error parsing page: {e}")
            else:
                print(f"  No calls found on this date")
        else:
            print(f"  ❌ Query failed: {response.status_code}")
    
    # Now check for unprocessed calls with transcripts
    print("\n" + "=" * 60)
    print("UNPROCESSED CALLS WITH TRANSCRIPTS (All dates):")
    print("=" * 60)
    
    filter_conditions = {
        "and": [
            {
                "property": "Status",
                "status": {"equals": "Recent Client Meeting"}
            },
            {
                "property": "Added to Google Chat",
                "checkbox": {"equals": False}
            },
            {
                "or": [
                    {
                        "property": "[NEW] GDrive Transcript URL",
                        "url": {"is_not_empty": True}
                    },
                    {
                        "property": "GDrive Transcript URL",
                        "url": {"is_not_empty": True}
                    }
                ]
            }
        ]
    }
    
    url = f"https://api.notion.com/v1/databases/{MEETING_DIARY_DB}/query"
    body = {
        "filter": filter_conditions,
        "page_size": 20,
        "sorts": [{"property": "Meeting Date", "direction": "descending"}]
    }
    
    response = requests.post(url, headers=NOTION_HEADERS, json=body)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        
        if results:
            print(f"\nFound {len(results)} unprocessed calls with transcripts:")
            
            for page in results:
                try:
                    props = page.get("properties", {})
                    
                    # Get date
                    call_date = "Unknown"
                    if "Meeting Date" in props:
                        date_prop = props["Meeting Date"]
                        if date_prop.get("date"):
                            call_date = date_prop["date"]["start"]
                    
                    # Get title
                    title = "Unknown"
                    if "Discovery" in props:
                        title_prop = props["Discovery"]
                        if title_prop.get("title"):
                            title = title_prop["title"][0]["plain_text"]
                    
                    # Get meeting type
                    meeting_type = "Unknown"
                    if "Meeting Type" in props:
                        mt_prop = props["Meeting Type"]
                        if mt_prop.get("select"):
                            meeting_type = mt_prop["select"]["name"]
                    
                    print(f"\n  📅 {call_date}: {title}")
                    print(f"     Type: {meeting_type}")
                    print(f"     URL: {page.get('url', 'N/A')}")
                    
                except Exception as e:
                    print(f"  Error: {e}")
        else:
            print("\nNo unprocessed calls with transcripts found.")
    else:
        print(f"\n❌ Query failed: {response.status_code}")

if __name__ == "__main__":
    check_calls_for_dates()