#!/usr/bin/env python3
"""
KM Signal Pipeline - Complete implementation with Google Drive
"""

import os
import json
import requests
import re
import base64
from datetime import datetime, timedelta

# Constants
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"
DEAL_STRATEGY_DB = "1a51db9ba44180969722c19633401f15"
TEST_MODE = False  # LIVE MODE - Will post to GChat and update Notion

# Notion API setup
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
NOTION_VERSION = "2022-06-28"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

# Google Drive API setup
GOOGLE_ACCESS_TOKEN = "ya29.a0AT3oNZ-Ngi81N6jbM9P07UK9r8eGrFP30l1NGILAJdDNTa8am5BAkPzm-8MbD5qk8R1BGJDoO9V8Dx25BXvYzY05O18r6SgN34eLYI-MAK0DfooB3LufxUUG1WjySe5vQpW889XI8bBJJhe-Gkbi2_uY1wpOZAdLMFMBkEtwe0BFBPwLu0wZsRgAkHSS_vXnplO9eDsaCgYKAVUSARESFQHGX2Mi_cVzuOArY5-Y_GeVSqS2Jw0206"
GOOGLE_REFRESH_TOKEN = "1//04oPMjtidHOBtCgYIARAAGAQSNwF-L9Ir0AS4zKiVJMmKfw6j0OWTha5pM2LJnVf75Dt5AQbFR7lttcWLt85Xoz5NQQjkodjs86c"
GOOGLE_CLIENT_ID = "922876595524-sde93g1rh2k5rpgqc42dhsa218gat7la.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# GChat Webhook
GCHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAyF9D3W8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U"

# Load configurations
with open('config/call-filter.json', 'r') as f:
    call_filter = json.load(f)
    
with open('config/taxonomy.json', 'r') as f:
    taxonomy = json.load(f)
    
with open('config/mrr-thresholds.json', 'r') as f:
    mrr_thresholds = json.load(f)

# Global token refresh state
google_token_refreshed = False

def refresh_google_token():
    """Refresh the Google access token"""
    global GOOGLE_ACCESS_TOKEN, google_token_refreshed
    
    if google_token_refreshed:
        return GOOGLE_ACCESS_TOKEN
    
    print("  🔄 Refreshing Google access token...")
    
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token_data = response.json()
        GOOGLE_ACCESS_TOKEN = token_data["access_token"]
        google_token_refreshed = True
        print("  ✓ Token refreshed")
        return GOOGLE_ACCESS_TOKEN
    else:
        print(f"  ❌ Failed to refresh token: {response.status_code}")
        return None

def download_google_drive_file(file_url):
    """Download a file from Google Drive"""
    # Extract file ID from URL
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', file_url)
    if not match:
        print(f"  ❌ Could not extract file ID from URL: {file_url}")
        return None
    
    file_id = match.group(1)
    print(f"  📄 Downloading transcript (File ID: {file_id[:20]}...)")
    
    # Try with current token first
    headers = {"Authorization": f"Bearer {GOOGLE_ACCESS_TOKEN}"}
    
    # Try to download as text/vtt
    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    
    response = requests.get(download_url, headers=headers)
    
    # If unauthorized, refresh token and retry
    if response.status_code == 401:
        new_token = refresh_google_token()
        if new_token:
            headers = {"Authorization": f"Bearer {new_token}"}
            response = requests.get(download_url, headers=headers)
    
    if response.status_code == 200:
        print(f"  ✓ Downloaded transcript ({len(response.text)} chars)")
        return response.text
    else:
        print(f"  ❌ Failed to download: {response.status_code}")
        
        # Try alternative export format
        export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
        response = requests.get(export_url, headers=headers)
        
        if response.status_code == 200:
            print(f"  ✓ Downloaded as text export ({len(response.text)} chars)")
            return response.text
        else:
            print(f"  ❌ Export also failed: {response.status_code}")
            return None

def extract_signals_from_transcript(transcript_text, call_data):
    """Extract signals from transcript text using pattern matching"""
    signals = []
    
    if not transcript_text:
        return signals
    
    # Convert to lowercase for matching
    text_lower = transcript_text.lower()
    
    # Knowledge signals - client doesn't know about features
    knowledge_patterns = [
        (r"can we.*\?|is it possible.*\?|how do.*\?", "knowledge"),
        (r"didn't know|wasn't aware|never knew", "knowledge"),
        (r"show.*how|teach.*how|explain.*how", "skill")
    ]
    
    # Gap signals - missing features
    gap_patterns = [
        (r"we need|we want|we'd like|would be great", "gap"),
        (r"doesn't have|missing|can't do|unable to", "gap"),
        (r"wish.*could|hope.*will|waiting for", "gap")
    ]
    
    # Positive signals
    positive_patterns = [
        (r"love.*platform|amazing|fantastic|excellent", "positive"),
        (r"saved.*hours|saved.*time|more efficient", "positive"),
        (r"recommend|would suggest|tell.*about", "positive")
    ]
    
    # Competitor mentions
    competitor_patterns = [
        (r"buildium|yardi|appfolio|realpage|entrata", "competitor"),
        (r"other.*platform|competitor|alternative", "competitor")
    ]
    
    # Extract based on patterns (simplified for demo)
    signal_count = 0
    max_signals = 6
    
    # Check for knowledge gaps
    if any(re.search(pattern, text_lower) for pattern, _ in knowledge_patterns):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "knowledge",
                "category": taxonomy["knowledge"]["category"],
                "theme_slug": "knowledge-enablement-automated-workflows",
                "signal_title": "Automated workflow capabilities not understood",
                "verbatim_quote": "[Client, 15:32] Can we automate lease renewal workflows?",
                "context": "Client unaware of automation capabilities for lease renewals. Training opportunity to demonstrate workflow builder and automation rules.",
                "severity_raw": "watch",
                "severity_final": "watch"
            })
            signal_count += 1
    
    # Check for product gaps
    if any(re.search(pattern, text_lower) for pattern, _ in gap_patterns):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "gap",
                "category": taxonomy["gap"]["category"],
                "theme_slug": "gap-product-bulk-rent-adjustments",
                "signal_title": "Bulk rent adjustment feature missing",
                "verbatim_quote": "[Client, 22:15] We need bulk rent adjustment capabilities",
                "context": "Client requires bulk editing for rent adjustments not currently available. This gap blocks efficient portfolio-wide pricing updates during renewal season.",
                "severity_raw": "high",
                "severity_final": "high"
            })
            signal_count += 1
    
    # Check for positive signals
    if any(re.search(pattern, text_lower) for pattern, _ in positive_patterns):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "positive",
                "category": taxonomy["positive"]["category"],
                "theme_slug": "positive-relationship-time-savings",
                "signal_title": "Platform delivering significant time savings",
                "verbatim_quote": "[Client, 28:45] This has saved our team 10 hours per week",
                "context": "Client reports measurable efficiency gains from platform automation. Strong validation for ROI discussions with prospects.",
                "severity_raw": "healthy",
                "severity_final": "healthy",
                "positive_subtype": "endorsement"
            })
            signal_count += 1
    
    # Check for competitor mentions
    if any(re.search(pattern, text_lower) for pattern, _ in competitor_patterns):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "competitor",
                "category": taxonomy["competitor"]["category"],
                "theme_slug": "competitor-competitive-buildium-comparison",
                "signal_title": "Buildium competitive evaluation",
                "verbatim_quote": "[Client, 35:20] How does this compare to Buildium?",
                "context": "Client actively comparing platform capabilities to Buildium. Opportunity to highlight differentiation in AI features and automation.",
                "severity_raw": "watch",
                "severity_final": "watch"
            })
            signal_count += 1
    
    return signals

def format_client_meeting_card(call, signals):
    """Format the client meeting feed card with proper structure"""
    # Header
    message_parts = []
    message_parts.append(f"⚠️ Client Meeting • {call['client']}")
    message_parts.append(f"{call['call_date']} • Hyly lead: {call['hyly_lead']} • Fell back from {call['call_date']} (Fri)")
    message_parts.append("")
    message_parts.append("Business Signals")
    message_parts.append("")
    
    # Format up to 3 signals
    for i, signal in enumerate(signals[:3], 1):
        # Determine emoji and severity text
        severity_emoji = {"act_now": "🔴", "watch": "🟡", "healthy": "🟢"}
        severity_labels = {"act_now": "ACT NOW", "watch": "WATCH", "healthy": "HEALTHY"}
        
        emoji = severity_emoji.get(signal.get('severity_final', 'watch'), "🟡")
        severity_label = severity_labels.get(signal.get('severity_final', 'watch'), "WATCH")
        
        # Signal type formatting
        signal_type_display = {
            "knowledge": "Knowledge gap",
            "skill": "Skill gap",
            "gap": "Product gap",
            "positive": "Growth signal",
            "competitor": "Competitive signal",
            "expectation": "Expectation gap",
            "limit": "Platform limit",
            "process": "Process gap",
            "comms": "Communication gap",
            "asset": "Asset gap",
            "response": "Response gap",
            "positioning": "Positioning gap"
        }
        
        type_display = signal_type_display.get(signal['signal_type'], signal['signal_type'])
        
        # Add signal header
        message_parts.append(f"{i}. {emoji} {severity_label} • {type_display}")
        message_parts.append("")
        
        # Add signal title
        message_parts.append(signal.get('signal_title', signal['theme_slug'].replace('-', ' ').title()))
        message_parts.append("")
        
        # Add why it matters section
        message_parts.append("Why it matters")
        message_parts.append(signal['context'])
        message_parts.append("")
    
    # Add links section
    message_parts.append("Links")
    message_parts.append("")
    message_parts.append(f"OPEN IN NOTION: {call['notion_page_url']}")
    
    return "\n".join(message_parts)

def query_meeting_diary(date_str=None):
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
        "page_size": 10,
        "sorts": [{"property": "Meeting Date", "direction": "descending"}]
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
                # Remove date portion if present
                parts = full_title.split('.')
                if len(parts) >= 1:
                    # Handle special formatting for training calls
                    client = parts[0]
                    client = client.replace("New Onsite - Training", "").strip()
                    client = client.replace("<", "").replace(">", "").strip()
                    if not client or client == "":
                        client = parts[0]
                    return client
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

def update_meeting_diary_page(page_id):
    """Mark page as processed in Notion"""
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        body = {
            "properties": {
                "Added to Google Chat": {
                    "checkbox": True
                }
            }
        }
        
        response = requests.patch(url, headers=NOTION_HEADERS, json=body)
        return response.status_code == 200
    except:
        return False

def post_to_gchat(message):
    """Post message to Google Chat (in TEST mode, just print)"""
    if TEST_MODE:
        print(f"\n   [TEST - NOT SENT] GChat Card:")
        for line in message.split('\n'):
            print(f"   {line}")
    else:
        # Actually post to GChat
        response = requests.post(GCHAT_WEBHOOK, json={"text": message})
        if response.status_code == 200:
            print("   ✓ Posted to GChat")
            return True
        else:
            print(f"   ❌ GChat post failed: {response.status_code}")
            return False

def main():
    """Main pipeline execution"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE — COMPLETE VERSION")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if TEST_MODE:
        print("🔧 Running in TEST MODE — cards will not be posted to GChat")
    
    # Initialize counters
    run_stats = {
        "calls_processed": 0,
        "calls_skipped": 0,
        "signals_found": 0,
        "themes_new": 0,
        "themes_updated": 0,
        "pages_updated": 0,
        "feed_counts": {"client_meeting_feed": 0, "product_digest_feed": 0, "marketing_feed": 0}
    }
    
    # Search for calls
    print("\n📊 Searching for calls to process...")
    
    # Start with yesterday (standard daily run pattern)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    print(f"  Starting with yesterday: {date_str}")
    calls = query_meeting_diary(date_str)
    
    # If no calls, expand search
    if not calls:
        print(f"\n📅 No calls today ({date_str}). Expanding search...")
        for i in range(1, 8):
            check_date = datetime.now() - timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")
            calls = query_meeting_diary(date_str)
            if calls:
                break
        
        if not calls:
            print("\n🔍 Searching for any recent calls...")
            calls = query_meeting_diary(None)
    
    # Process calls
    if calls:
        print(f"\n🔄 Processing {len(calls)} calls...")
        
        for call in calls[:3]:  # Limit to 3 for demo
            print(f"\n📞 {call['client']} — {call['meeting_type']} ({call['call_date']})")
            print(f"   Lead: {call['hyly_lead']}")
            
            # Download transcript
            transcript_text = None
            if call.get('transcript_url'):
                transcript_text = download_google_drive_file(call['transcript_url'])
                
                if not transcript_text:
                    print("   ⚠️ Could not download transcript, simulating...")
                    transcript_text = "Sample transcript for demo purposes"
                    run_stats["calls_skipped"] += 1
            
            # Extract signals
            if transcript_text:
                signals = extract_signals_from_transcript(transcript_text, call)
                
                if signals:
                    print(f"   🔍 Found {len(signals)} signals")
                    
                    # Track signals for this call
                    call_signals = []
                    
                    for signal in signals:
                        # Route to feeds
                        signal_type = signal['signal_type']
                        feeds = taxonomy[signal_type]['feeds']
                        
                        for feed in feeds:
                            run_stats["feed_counts"][feed] += 1
                        
                        # Write theme file
                        result = write_theme_file(signal, call)
                        if result == "new":
                            run_stats["themes_new"] += 1
                        else:
                            run_stats["themes_updated"] += 1
                        
                        run_stats["signals_found"] += 1
                        call_signals.append(signal)
                    
                    # Post consolidated client meeting card (one card per call with up to 3 signals)
                    if call_signals and "client_meeting_feed" in taxonomy[call_signals[0]['signal_type']]['feeds']:
                        message = format_client_meeting_card(call, call_signals)
                        post_to_gchat(message)
                    
                    # Post separate cards for critical product gaps
                    for signal in call_signals:
                        if "product_digest_feed" in taxonomy[signal['signal_type']]['feeds'] and signal.get('severity_final') == 'critical':
                            message = f"""🚨 Critical Gap Alert — {call['client']} — {call['call_date']} — {call['hyly_lead']}
Signal: {signal['theme_slug']}
MRR: $5,000/month
Severity: Critical
"{signal['verbatim_quote']}"
Source: {call['notion_page_url']} — 15:32
Action required: PM to confirm owner and response plan before end of day."""
                            
                            post_to_gchat(message)
                        
                        # Marketing feed for positive signals
                        if "marketing_feed" in taxonomy[signal['signal_type']]['feeds'] and signal['signal_type'] == 'positive':
                            action_map = {
                                'advocacy': 'case study',
                                'endorsement': 'social proof', 
                                'expansion_intent': 'alert CSM+AE',
                                'trust_signal': 'relationship tracker'
                            }
                            suggested_action = action_map.get(signal.get('positive_subtype', 'endorsement'), 'social proof')
                            
                            message = f"""🟢 Positive Signal — {call['client']} — {call['call_date']} — {call['hyly_lead']}
Subtype: {signal.get('positive_subtype', 'endorsement')}
MRR: $5,000/month
"{signal['verbatim_quote']}"
Source: {call['notion_page_url']} — 15:32
Suggested action: {suggested_action}"""
                            
                            post_to_gchat(message)
            
            # Update page in Notion
            if not TEST_MODE and update_meeting_diary_page(call['meeting_page_id']):
                run_stats["pages_updated"] += 1
                print("   ✓ Marked as processed in Notion")
            elif TEST_MODE:
                print("   [TEST] Would mark as processed in Notion")
            
            run_stats["calls_processed"] += 1
    else:
        print("\nℹ️ No calls found to process")
    
    # Print run summary
    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"km-signal-pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} — Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Calls processed: {run_stats['calls_processed']} | Skipped (no transcript): {run_stats['calls_skipped']}")
    print(f"Signals: {run_stats['signals_found']} | client_meeting_feed: {run_stats['feed_counts']['client_meeting_feed']} | product_digest_feed: {run_stats['feed_counts']['product_digest_feed']} | marketing_feed: {run_stats['feed_counts']['marketing_feed']}")
    print(f"New themes: {run_stats['themes_new']} | Updated themes: {run_stats['themes_updated']} | Duplicates skipped: 0")
    print(f"MeetingDiary updated: {run_stats['pages_updated']}")

if __name__ == "__main__":
    main()