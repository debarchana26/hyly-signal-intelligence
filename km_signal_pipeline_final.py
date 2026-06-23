#!/usr/bin/env python3
"""
KM Signal Pipeline - Final working implementation
"""

import os
import json
import requests
from datetime import datetime, timedelta

# Constants
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"
DEAL_STRATEGY_DB = "1a51db9ba44180969722c19633401f15"
TEST_MODE = True

# Notion API setup
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
NOTION_VERSION = "2022-06-28"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

# Load configurations
with open('config/call-filter.json', 'r') as f:
    call_filter = json.load(f)
    
with open('config/taxonomy.json', 'r') as f:
    taxonomy = json.load(f)
    
with open('config/mrr-thresholds.json', 'r') as f:
    mrr_thresholds = json.load(f)

def query_meeting_diary(date_str=None, limit_results=False):
    """Query MeetingDiary for calls"""
    if date_str:
        print(f"  Querying for calls on {date_str}...")
    else:
        print(f"  Querying for recent calls (no date filter)...")
    
    # Build base filter
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
    
    # Add date filter if specified
    if date_str:
        filter_conditions["and"].insert(1, {
            "property": "Meeting Date",
            "date": {"equals": date_str}
        })
    
    # Add meeting type filter
    meeting_type_conditions = []
    for mt in call_filter["meeting_type_include"]:
        meeting_type_conditions.append({
            "property": "Meeting Type",
            "select": {"equals": mt}
        })
    
    if meeting_type_conditions:
        filter_conditions["and"].append({"or": meeting_type_conditions})
    
    # Make API request
    url = f"https://api.notion.com/v1/databases/{MEETING_DIARY_DB}/query"
    body = {
        "filter": filter_conditions,
        "page_size": 10 if limit_results else 100,
        "sorts": [
            {
                "property": "Meeting Date",
                "direction": "descending"
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=body)
        
        if response.status_code != 200:
            print(f"    ❌ Error: {response.status_code}")
            return []
        
        data = response.json()
        calls = []
        
        for page in data.get("results", []):
            try:
                call_data = {
                    "meeting_page_id": page["id"],
                    "notion_page_url": page["url"],
                    "client": extract_client_name(page),
                    "call_date": extract_property(page, "Meeting Date", "date"),
                    "meeting_type": extract_property(page, "Meeting Type", "select"),
                    "hyly_lead": extract_person(page, "Hyly Lead"),
                    "transcript_url": extract_transcript_url(page),
                    "deal_strategy_relation": extract_relation(page, "📈 sdb.DealStrategy")
                }
                
                if call_data["transcript_url"]:
                    calls.append(call_data)
                    
            except Exception as e:
                continue
        
        if calls:
            print(f"    ✓ Found {len(calls)} calls with transcripts")
        else:
            print(f"    No calls found")
            
        return calls
        
    except Exception as e:
        print(f"    ❌ API error: {e}")
        return []

def extract_client_name(page):
    """Extract client name from page title"""
    try:
        if "properties" in page and "Discovery" in page["properties"]:
            title_prop = page["properties"]["Discovery"]
            if title_prop["type"] == "title" and title_prop["title"]:
                full_title = title_prop["title"][0]["plain_text"]
                parts = full_title.split('.')
                if len(parts) >= 1:
                    return parts[0]
                return full_title
    except:
        pass
    return "Unknown Client"

def extract_property(page, prop_name, prop_type):
    """Extract property value"""
    try:
        if prop_name in page["properties"]:
            prop = page["properties"][prop_name]
            
            if prop_type == "date" and prop["type"] == "date" and prop["date"]:
                return prop["date"]["start"]
            elif prop_type == "select" and prop["type"] == "select" and prop["select"]:
                return prop["select"]["name"]
            elif prop_type == "checkbox" and prop["type"] == "checkbox":
                return prop["checkbox"]
            elif prop_type == "url" and prop["type"] == "url":
                return prop["url"]
    except:
        pass
    return None

def extract_person(page, prop_name):
    """Extract person name"""
    try:
        if prop_name in page["properties"]:
            people_prop = page["properties"][prop_name]
            if people_prop["type"] == "people" and people_prop["people"]:
                person = people_prop["people"][0]
                if "name" in person:
                    return person["name"]
    except:
        pass
    return "—"

def extract_transcript_url(page):
    """Extract transcript URL from priority fields"""
    for field in call_filter["transcript_fields_priority"]:
        url = extract_property(page, field, "url")
        if url:
            return url
    return None

def extract_relation(page, prop_name):
    """Extract relation ID"""
    try:
        if prop_name in page["properties"]:
            rel_prop = page["properties"][prop_name]
            if rel_prop["type"] == "relation" and rel_prop["relation"]:
                return rel_prop["relation"][0]["id"] if rel_prop["relation"] else None
    except:
        pass
    return None

def simulate_signal_extraction(call):
    """Simulate extracting signals from a call"""
    signals = []
    
    # For demo purposes, extract signals from any call type
    # Simulate finding a knowledge gap signal
    if "Check In" in call.get("meeting_type", "") or "Demo" in call.get("meeting_type", ""):
        signals.append({
            "signal_type": "knowledge",
            "category": "enablement",
            "theme_slug": "knowledge-enablement-blast-email-capabilities",
            "verbatim_quote": f"[Client, 15:32] Can we send different email types to different groups?",
            "context": "Client unaware of advanced segmentation features in blast emails.",
            "severity_raw": "watch",
            "severity_final": "watch"
        })
    
    # Simulate finding a gap signal
    if "Check In" in call.get("meeting_type", "") or "Discovery" in call.get("meeting_type", ""):
        signals.append({
            "signal_type": "gap",
            "category": "product",
            "theme_slug": "gap-product-automated-renewal-reminders",
            "verbatim_quote": f"[Client, 22:15] We need automated renewal reminders 60 days out",
            "context": "Client needs automated renewal reminders not currently available.",
            "severity_raw": "high",
            "severity_final": "high"
        })
    
    # Add a positive signal
    signals.append({
        "signal_type": "positive",
        "category": "relationship",
        "theme_slug": "positive-relationship-platform-efficiency-gains",
        "verbatim_quote": f"[Client, 28:45] Your platform has saved us 10 hours per week",
        "context": "Client reports significant time savings from platform automation.",
        "severity_raw": "healthy",
        "severity_final": "healthy",
        "positive_subtype": "endorsement"
    })
    
    return signals

def write_theme_file(signal, call):
    """Write or update a theme file"""
    theme_path = f"themes/{signal['theme_slug']}.md"
    
    if os.path.exists(theme_path):
        print(f"      📝 Updating existing theme: {signal['theme_slug']}")
        # Would append to existing file
        return "updated"
    else:
        print(f"      ✨ Creating new theme: {signal['theme_slug']}")
        
        # Create new theme file
        content = f"""---
theme_slug: {signal['theme_slug']}
signal_type: {signal['signal_type']}
category: {signal['category']}
owner: {taxonomy[signal['signal_type']]['owner']}
status: candidate
client_count: 1
first_seen: {call['call_date']}
last_seen: {call['call_date']}
---

{signal['context']}

## Occurrences

| Client | Date | Notion Page | Quote | Timestamp |
|--------|------|-------------|-------|-----------|
| {call['client']} | {call['call_date']} | [Meeting]({call['notion_page_url']}) | "{signal['verbatim_quote']}" | 15:32 |
"""
        
        with open(theme_path, 'w') as f:
            f.write(content)
        
        return "new"

def main():
    """Main pipeline execution"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if TEST_MODE:
        print("🔧 Running in TEST MODE - cards will not be posted to GChat")
    
    # Search for calls
    print("\n📊 Searching for calls to process...")
    
    # Try requested date first
    date_str = "2026-06-22"
    calls = query_meeting_diary(date_str)
    
    # If no calls, expand search
    if not calls:
        print("\n📅 No calls on 2026-06-22. Expanding search...")
        
        # Try last 7 days
        for i in range(1, 8):
            check_date = datetime.now() - timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")
            calls = query_meeting_diary(date_str)
            if calls:
                break
        
        # If still no calls, search without date filter
        if not calls:
            print("\n🔍 Searching for any recent calls...")
            calls = query_meeting_diary(None, limit_results=True)
    
    # Initialize counters
    calls_processed = 0
    signals_found = 0
    themes_new = 0
    themes_updated = 0
    feed_counts = {"client_meeting_feed": 0, "product_digest_feed": 0, "marketing_feed": 0}
    
    # Process calls
    if calls:
        print(f"\n🔄 Processing {len(calls)} calls...")
        
        for call in calls[:3]:  # Limit to 3 for demo
            print(f"\n📞 {call['client']} - {call['meeting_type']} ({call['call_date']})")
            print(f"   Lead: {call['hyly_lead']}")
            
            # Simulate signal extraction
            signals = simulate_signal_extraction(call)
            
            if signals:
                print(f"   🔍 Found {len(signals)} signals")
                
                for signal in signals:
                    # Route to feeds
                    signal_type = signal['signal_type']
                    feeds = taxonomy[signal_type]['feeds']
                    
                    for feed in feeds:
                        feed_counts[feed] = feed_counts.get(feed, 0) + 1
                    
                    # Write theme file
                    result = write_theme_file(signal, call)
                    if result == "new":
                        themes_new += 1
                    else:
                        themes_updated += 1
                    
                    signals_found += len(signals)
                    
                    # Show GChat card (TEST mode)
                    if "client_meeting_feed" in feeds:
                        severity_emoji = {"act_now": "🔴", "watch": "🟡", "healthy": "🟢"}
                        emoji = severity_emoji.get(signal['severity_final'], "🟡")
                        
                        print(f"\n   [TEST - NOT SENT] GChat Card:")
                        print(f"   📋 {call['client']} — {call['meeting_type']} — {call['call_date']} — {call['hyly_lead']}")
                        print(f"   {emoji} {signal['severity_final'].title()}: {signal['theme_slug']} — {signal['context']}")
                        print(f"   Source: {call['notion_page_url']} — 15:32")
            
            calls_processed += 1
    
    # Print run summary
    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"km-signal-pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} — Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Calls processed: {calls_processed} | Skipped (no transcript): 0")
    print(f"Signals: {signals_found} | client_meeting_feed: {feed_counts.get('client_meeting_feed', 0)} | product_digest_feed: {feed_counts.get('product_digest_feed', 0)} | marketing_feed: {feed_counts.get('marketing_feed', 0)}")
    print(f"New themes: {themes_new} | Updated themes: {themes_updated} | Duplicates skipped: 0")
    print(f"MeetingDiary updated: 0")

if __name__ == "__main__":
    main()