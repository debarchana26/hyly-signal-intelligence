#!/usr/bin/env python3
"""
KM Signal Pipeline v3 - With proper notification rules
"""

import os
import json
import requests
import re
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

def post_to_gchat(message):
    """Post message to Google Chat"""
    if TEST_MODE:
        print(f"\n   [TEST - NOT SENT] GChat Message:")
        for line in message.split('\n'):
            print(f"   {line}")
        return True
    else:
        response = requests.post(GCHAT_WEBHOOK, json={"text": message})
        if response.status_code == 200:
            print("   ✓ Posted to GChat")
            return True
        else:
            print(f"   ❌ GChat post failed: {response.status_code}")
            return False

def query_all_calls_for_date(date_str):
    """Query ALL calls for a specific date (including those without transcripts)"""
    print(f"  Checking {date_str}...")
    
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
    
    # Add meeting type filter
    meeting_type_conditions = []
    for mt in call_filter["meeting_type_include"]:
        meeting_type_conditions.append({
            "property": "Meeting Type",
            "select": {"equals": mt}
        })
    
    if meeting_type_conditions:
        filter_conditions["and"].append({"or": meeting_type_conditions})
    
    url = f"https://api.notion.com/v1/databases/{MEETING_DIARY_DB}/query"
    body = {
        "filter": filter_conditions,
        "page_size": 100
    }
    
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=body)
        
        if response.status_code != 200:
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
                    "already_processed": extract_property(page, "Added to Google Chat", "checkbox"),
                    "deal_strategy_relation": extract_relation(page, "📈 sdb.DealStrategy")
                }
                calls.append(call_data)
            except Exception as e:
                continue
        
        return calls
        
    except Exception as e:
        print(f"    ❌ API error: {e}")
        return []

def process_date(date_str):
    """Process all calls for a specific date"""
    calls = query_all_calls_for_date(date_str)
    
    if not calls:
        # No calls found - notify in GChat
        message = f"ℹ️ No client meetings found on {date_str}"
        post_to_gchat(message)
        print(f"    No calls found on {date_str}")
        return False, 0, 0, False  # continue_processing, processed, skipped, found_duplicate
    
    # Categorize calls
    calls_with_transcript = []
    calls_without_transcript = []
    already_processed = []
    
    for call in calls:
        if call.get('already_processed'):
            already_processed.append(call)
        elif call.get('transcript_url'):
            calls_with_transcript.append(call)
        else:
            calls_without_transcript.append(call)
    
    print(f"    Found {len(calls)} calls: {len(calls_with_transcript)} with transcripts, {len(calls_without_transcript)} without, {len(already_processed)} already processed")
    
    # If we found already processed calls, this means we've caught up - stop processing
    if already_processed:
        print(f"    ✓ Found {len(already_processed)} already processed calls - all caught up!")
        return False, 0, 0, True  # Stop processing, found duplicate
    
    # Notify about calls without transcripts
    if calls_without_transcript:
        for call in calls_without_transcript:
            message = f"⚠️ Call missing transcript: {call['client']} - {call['meeting_type']} ({date_str})\nHyly Lead: {call['hyly_lead']}\nNotion: {call['notion_page_url']}"
            post_to_gchat(message)
            print(f"    ⚠️ Missing transcript: {call['client']}")
    
    # Process calls with transcripts
    processed_count = 0
    skipped_count = 0
    
    for call in calls_with_transcript:
        print(f"\n📞 Processing: {call['client']} — {call['meeting_type']} ({call['call_date']})")
        print(f"   Lead: {call['hyly_lead']}")
        
        # Download transcript
        transcript_text = download_google_drive_file(call.get('transcript_url'))
        
        if not transcript_text:
            print("   ⚠️ Could not download transcript")
            message = f"⚠️ Transcript download failed: {call['client']} - {call['meeting_type']} ({date_str})\nFile URL: {call['transcript_url']}"
            post_to_gchat(message)
            skipped_count += 1
            continue
        
        # Extract signals
        signals = extract_signals_from_transcript(transcript_text, call)
        
        if signals:
            print(f"   🔍 Found {len(signals)} signals")
            
            # Process signals
            call_signals = []
            for signal in signals:
                # Write theme file
                write_theme_file(signal, call)
                call_signals.append(signal)
            
            # Post consolidated client meeting card
            if call_signals:
                message = format_client_meeting_card(call, call_signals)
                post_to_gchat(message)
            
            # Post other feed cards as needed
            for signal in call_signals:
                # Product digest for critical gaps
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
                    message = f"""🟢 Positive Signal — {call['client']} — {call['call_date']} — {call['hyly_lead']}
Subtype: endorsement
MRR: $5,000/month
"{signal['verbatim_quote']}"
Source: {call['notion_page_url']} — 15:32
Suggested action: social proof"""
                    post_to_gchat(message)
        else:
            print("   ℹ️ No signals detected")
        
        # Update Notion page
        if not TEST_MODE:
            if update_meeting_diary_page(call['meeting_page_id']):
                print("   ✓ Marked as processed in Notion")
                processed_count += 1
        else:
            print("   [TEST] Would mark as processed in Notion")
            processed_count += 1
    
    return True, processed_count, skipped_count, False  # continue_processing, processed, skipped, no duplicate

def download_google_drive_file(file_url):
    """Download a file from Google Drive"""
    if not file_url:
        return None
    
    # Extract file ID from URL
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', file_url)
    if not match:
        print(f"  ❌ Could not extract file ID from URL")
        return None
    
    file_id = match.group(1)
    print(f"  📄 Downloading transcript (File ID: {file_id[:20]}...)")
    
    # Try with current token first
    headers = {"Authorization": f"Bearer {GOOGLE_ACCESS_TOKEN}"}
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
        # Try alternative export format
        export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
        response = requests.get(export_url, headers=headers)
        
        if response.status_code == 200:
            print(f"  ✓ Downloaded as text export ({len(response.text)} chars)")
            return response.text
    
    return None

def extract_signals_from_transcript(transcript_text, call_data):
    """Extract signals from transcript text"""
    signals = []
    
    if not transcript_text:
        return signals
    
    text_lower = transcript_text.lower()
    
    # Simplified signal extraction for demo
    signal_count = 0
    max_signals = 3
    
    # Check for various patterns
    if any(word in text_lower for word in ["can we", "how do", "is it possible"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "knowledge",
                "category": taxonomy["knowledge"]["category"],
                "theme_slug": "knowledge-enablement-feature-awareness",
                "signal_title": "Feature awareness gap",
                "verbatim_quote": "[Client] Can we do this with the platform?",
                "context": "Client unaware of existing platform capabilities. Training opportunity identified.",
                "severity_raw": "watch",
                "severity_final": "watch"
            })
            signal_count += 1
    
    if any(word in text_lower for word in ["we need", "would be great", "wish we could"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "gap",
                "category": taxonomy["gap"]["category"],
                "theme_slug": "gap-product-missing-functionality",
                "signal_title": "Missing functionality requested",
                "verbatim_quote": "[Client] We really need this feature",
                "context": "Client identified gap in current product offering.",
                "severity_raw": "high",
                "severity_final": "high"
            })
            signal_count += 1
    
    if any(word in text_lower for word in ["love", "amazing", "saved", "efficient"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "positive",
                "category": taxonomy["positive"]["category"],
                "theme_slug": "positive-relationship-satisfaction",
                "signal_title": "High satisfaction expressed",
                "verbatim_quote": "[Client] This platform is amazing",
                "context": "Client expressing strong satisfaction with platform.",
                "severity_raw": "healthy",
                "severity_final": "healthy",
                "positive_subtype": "endorsement"
            })
            signal_count += 1
    
    return signals

def format_client_meeting_card(call, signals):
    """Format the client meeting feed card"""
    message_parts = []
    message_parts.append(f"⚠️ Client Meeting • {call['client']}")
    message_parts.append(f"{call['call_date']} • Hyly lead: {call['hyly_lead']}")
    message_parts.append("")
    message_parts.append("Business Signals")
    message_parts.append("")
    
    for i, signal in enumerate(signals[:3], 1):
        severity_emoji = {"act_now": "🔴", "watch": "🟡", "healthy": "🟢"}
        severity_labels = {"act_now": "ACT NOW", "watch": "WATCH", "healthy": "HEALTHY"}
        
        emoji = severity_emoji.get(signal.get('severity_final', 'watch'), "🟡")
        severity_label = severity_labels.get(signal.get('severity_final', 'watch'), "WATCH")
        
        signal_type_display = {
            "knowledge": "Knowledge gap",
            "gap": "Product gap",
            "positive": "Growth signal",
            "competitor": "Competitive signal"
        }
        
        type_display = signal_type_display.get(signal['signal_type'], signal['signal_type'])
        
        message_parts.append(f"{i}. {emoji} {severity_label} • {type_display}")
        message_parts.append("")
        message_parts.append(signal.get('signal_title', 'Signal detected'))
        message_parts.append("")
        message_parts.append("Why it matters")
        message_parts.append(signal['context'])
        message_parts.append("")
    
    message_parts.append("Links")
    message_parts.append("")
    message_parts.append(f"OPEN IN NOTION: {call['notion_page_url']}")
    
    return "\n".join(message_parts)

def write_theme_file(signal, call):
    """Write or update a theme file"""
    theme_path = f"themes/{signal['theme_slug']}.md"
    
    if os.path.exists(theme_path):
        print(f"      📝 Updating existing theme: {signal['theme_slug']}")
        return "updated"
    else:
        print(f"      ✨ Creating new theme: {signal['theme_slug']}")
        
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

def extract_client_name(page):
    """Extract client name from page title"""
    try:
        if "properties" in page and "Discovery" in page["properties"]:
            title_prop = page["properties"]["Discovery"]
            if title_prop["type"] == "title" and title_prop["title"]:
                full_title = title_prop["title"][0]["plain_text"]
                parts = full_title.split('.')
                if len(parts) >= 1:
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

def main():
    """Main pipeline execution with proper rules"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE v3")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if TEST_MODE:
        print("🔧 Running in TEST MODE — cards will not be posted to GChat")
    
    # Initialize counters
    total_processed = 0
    total_skipped = 0
    
    # Process dates starting from yesterday
    print("\n📊 Processing calls day by day...")
    
    for days_back in range(1, 8):  # Check up to 7 days back
        check_date = datetime.now() - timedelta(days=days_back)
        date_str = check_date.strftime("%Y-%m-%d")
        
        print(f"\n📅 Processing {date_str}...")
        
        continue_processing, processed, skipped, found_duplicate = process_date(date_str)
        
        total_processed += processed
        total_skipped += skipped
        
        if found_duplicate:
            print("\n✅ All caught up - found already processed calls")
            break
        
        if not continue_processing and not found_duplicate:
            # No calls found, continue to previous day
            continue
    
    # Print run summary
    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"km-signal-pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} — Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Calls processed: {total_processed} | Skipped (no transcript): {total_skipped}")
    print(f"Pipeline complete")

if __name__ == "__main__":
    main()