#!/usr/bin/env python3
"""
KM Signal Pipeline - Direct Notion API implementation
"""

import os
import json
from datetime import datetime, timedelta
from notion_client import Client

# Constants from the skill - ensure proper formatting
MEETING_DIARY_DB = "f22d8083-6d1d-4759-a1c0-c133a4cce8c9"  # Added dashes for proper UUID format
DEAL_STRATEGY_DB = "1a51db9b-a441-8096-9722-c19633401f15"  # Added dashes for proper UUID format
TEST_MODE = True

# Initialize Notion client
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
notion = Client(auth=NOTION_TOKEN)

# Load configurations
with open('config/call-filter.json', 'r') as f:
    call_filter = json.load(f)
    
with open('config/taxonomy.json', 'r') as f:
    taxonomy = json.load(f)
    
with open('config/mrr-thresholds.json', 'r') as f:
    mrr_thresholds = json.load(f)

def get_date_window():
    """Get the date window for querying calls"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # For now, just use yesterday (2026-06-22)
    return yesterday.strftime("%Y-%m-%d")

def query_meeting_diary(date_str):
    """Query MeetingDiary for calls on the given date"""
    print(f"\n📊 Querying MeetingDiary for calls on {date_str}...")
    
    try:
        # Build the filter
        filter_conditions = {
            "and": [
                {
                    "property": "Status",
                    "select": {
                        "equals": "Recent Client Meeting"
                    }
                },
                {
                    "property": "Meeting Date",
                    "date": {
                        "equals": date_str
                    }
                },
                {
                    "property": "Added to Google Chat",
                    "checkbox": {
                        "equals": False
                    }
                },
                {
                    "or": [
                        {
                            "property": "[NEW] GDrive Transcript URL",
                            "url": {
                                "is_not_empty": True
                            }
                        },
                        {
                            "property": "GDrive Transcript URL",
                            "url": {
                                "is_not_empty": True
                            }
                        }
                    ]
                }
            ]
        }
        
        # Add meeting type filter
        meeting_type_conditions = []
        for mt in call_filter["meeting_type_include"]:
            meeting_type_conditions.append({
                "property": "Meeting Type",
                "select": {
                    "equals": mt
                }
            })
        
        if meeting_type_conditions:
            filter_conditions["and"].append({
                "or": meeting_type_conditions
            })
        
        # Query the database using direct API request
        response = notion.request(
            path=f"databases/{MEETING_DIARY_DB}/query",
            method="POST",
            body={
                "filter": filter_conditions
            }
        )
        
        calls = []
        for page in response.get("results", []):
            try:
                # Extract call data
                call_data = {
                    "meeting_page_id": page["id"],
                    "notion_page_url": page["url"],
                    "client": extract_client_name(page),
                    "call_date": extract_date(page, "Meeting Date"),
                    "meeting_type": extract_select(page, "Meeting Type"),
                    "hyly_lead": extract_person(page, "Hyly Lead"),
                    "transcript_url": extract_transcript_url(page),
                    "deal_strategy_relation": extract_relation(page, "📈 sdb.DealStrategy")
                }
                calls.append(call_data)
                print(f"  ✓ Found call: {call_data['client']} - {call_data['meeting_type']}")
            except Exception as e:
                print(f"  ⚠️ Error parsing page: {e}")
                continue
        
        print(f"\n📋 Found {len(calls)} calls to process")
        return calls
        
    except Exception as e:
        print(f"❌ Error querying MeetingDiary: {e}")
        return []

def extract_client_name(page):
    """Extract client name from page title"""
    try:
        # Try title property first
        if "properties" in page and "Discovery" in page["properties"]:
            title_prop = page["properties"]["Discovery"]
            if title_prop["type"] == "title" and title_prop["title"]:
                return title_prop["title"][0]["plain_text"]
        
        # Fallback to page title
        if "properties" in page and "Name" in page["properties"]:
            title_prop = page["properties"]["Name"]
            if title_prop["type"] == "title" and title_prop["title"]:
                return title_prop["title"][0]["plain_text"]
    except:
        pass
    return "Unknown Client"

def extract_date(page, prop_name):
    """Extract date from property"""
    try:
        if prop_name in page["properties"]:
            date_prop = page["properties"][prop_name]
            if date_prop["type"] == "date" and date_prop["date"]:
                return date_prop["date"]["start"]
    except:
        pass
    return None

def extract_select(page, prop_name):
    """Extract select value from property"""
    try:
        if prop_name in page["properties"]:
            select_prop = page["properties"][prop_name]
            if select_prop["type"] == "select" and select_prop["select"]:
                return select_prop["select"]["name"]
    except:
        pass
    return None

def extract_person(page, prop_name):
    """Extract person name from property"""
    try:
        if prop_name in page["properties"]:
            people_prop = page["properties"][prop_name]
            if people_prop["type"] == "people" and people_prop["people"]:
                # Get first person's name
                person = people_prop["people"][0]
                if "name" in person:
                    return person["name"]
    except:
        pass
    return "—"

def extract_transcript_url(page):
    """Extract transcript URL from priority fields"""
    for field in call_filter["transcript_fields_priority"]:
        try:
            if field in page["properties"]:
                url_prop = page["properties"][field]
                if url_prop["type"] == "url" and url_prop["url"]:
                    return url_prop["url"]
        except:
            continue
    return None

def extract_relation(page, prop_name):
    """Extract relation ID from property"""
    try:
        if prop_name in page["properties"]:
            rel_prop = page["properties"][prop_name]
            if rel_prop["type"] == "relation" and rel_prop["relation"]:
                return rel_prop["relation"][0]["id"] if rel_prop["relation"] else None
    except:
        pass
    return None

def main():
    """Main pipeline execution"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if TEST_MODE:
        print("🔧 Running in TEST MODE - cards will not be posted to GChat")
    
    # Step 1: Get date window and query calls
    date_str = get_date_window()
    calls = query_meeting_diary(date_str)
    
    # Initialize counters
    calls_processed = len(calls)
    signals_found = 0
    themes_new = 0
    themes_updated = 0
    
    if not calls:
        print("\nℹ️ No new calls found to process")
    else:
        print(f"\n🔄 Processing {len(calls)} calls...")
        # Here we would continue with transcript download, signal extraction, etc.
        # For now, just show what we found
    
    # Print run summary
    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"km-signal-pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} — Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Calls processed: {calls_processed} | Skipped (no transcript): 0")
    print(f"Signals: {signals_found} | client_meeting_feed: 0 | product_digest_feed: 0 | marketing_feed: 0")
    print(f"New themes: {themes_new} | Updated themes: {themes_updated} | Duplicates skipped: 0")
    print(f"MeetingDiary updated: 0")
    
    return calls

if __name__ == "__main__":
    calls = main()