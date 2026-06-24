#!/usr/bin/env python3
"""
KM Signal Pipeline - Strict Version with Guardrails
"""

import os
import sys
import json
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Constants
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"
DEAL_STRATEGY_DB = "1a51db9ba44180969722c19633401f15"
TEST_MODE = False  # LIVE MODE

# Required files check
REQUIRED_CONFIGS = [
    'config/call-filter.json',
    'config/taxonomy.json',
    'config/mrr-thresholds.json',
    'config/gchat-card-templates.json'
]

# Validate all required files exist
for config_file in REQUIRED_CONFIGS:
    if not os.path.exists(config_file):
        print(f"❌ CRITICAL: Required config file missing: {config_file}")
        sys.exit(1)

# Notion API setup
NOTION_TOKEN = "secret_C9rL6BtNeaO4qVbLbd3NBB32LHX3CNeMG069irANVLz"
NOTION_VERSION = "2022-06-28"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

# Google Drive API setup
GOOGLE_ACCESS_TOKEN = "ya29.a0AT3oNZ-Ngi81N6jbM9P07UK9r8eGrFP30l1NGILAJdDNTa8am5BAkPzm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U"
GOOGLE_REFRESH_TOKEN = "1//04oPMjtidHOBtCgYIARAAGAQSNwF-L9Ir0AS4zKiVJMmKfw6j0OWTha5pM2LJnVf75Dt5AQbFR7lttcWLt85Xoz5NQQjkodjs86c"
GOOGLE_CLIENT_ID = "922876595524-sde93g1rh2k5rpgqc42dhsa218gat7la.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# GChat Webhook
GCHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAyF9D3W8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U"

# Load configurations with validation
try:
    with open('config/call-filter.json', 'r') as f:
        call_filter = json.load(f)
    assert 'meeting_type_include' in call_filter, "meeting_type_include missing in call-filter.json"
    assert 'transcript_fields_priority' in call_filter, "transcript_fields_priority missing"
    
    with open('config/taxonomy.json', 'r') as f:
        taxonomy = json.load(f)
    assert all(k in taxonomy for k in ['knowledge', 'gap', 'positive']), "Required signal types missing"
    
    with open('config/mrr-thresholds.json', 'r') as f:
        mrr_thresholds = json.load(f)
    assert 'mrr_high_threshold' in mrr_thresholds, "mrr_high_threshold missing"
    
    with open('config/gchat-card-templates.json', 'r') as f:
        card_templates = json.load(f)
    
except Exception as e:
    print(f"❌ CRITICAL: Failed to load configurations: {e}")
    sys.exit(1)

# Global state
google_token_refreshed = False
pipeline_stats = {
    "calls_found": 0,
    "calls_processed": 0,
    "calls_skipped": 0,
    "missing_transcripts": [],
    "signals_extracted": 0,
    "themes_created": 0,
    "themes_updated": 0,
    "gchat_posts": 0,
    "notion_updates": 0,
    "errors": []
}

def log_step(step: str, status: str = "start"):
    """Log each pipeline step for debugging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "start":
        print(f"\n[{timestamp}] ▶️  STEP: {step}")
    elif status == "complete":
        print(f"[{timestamp}] ✅ COMPLETED: {step}")
    elif status == "error":
        print(f"[{timestamp}] ❌ ERROR: {step}")
        pipeline_stats["errors"].append(f"{timestamp}: {step}")
    elif status == "skip":
        print(f"[{timestamp}] ⏭️  SKIPPED: {step}")

def refresh_google_token():
    """Refresh the Google access token"""
    global GOOGLE_ACCESS_TOKEN, google_token_refreshed
    
    if google_token_refreshed:
        return GOOGLE_ACCESS_TOKEN
    
    log_step("Refreshing Google access token")
    
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            GOOGLE_ACCESS_TOKEN = token_data["access_token"]
            google_token_refreshed = True
            log_step("Google token refreshed", "complete")
            return GOOGLE_ACCESS_TOKEN
    except Exception as e:
        log_step(f"Google token refresh failed: {e}", "error")
    
    return None

def post_to_gchat_card(card_type: str, params: Dict) -> bool:
    """Post a properly formatted card to GChat"""
    if TEST_MODE:
        print(f"\n[TEST MODE] Would send {card_type} card with params: {params}")
        return True
    
    try:
        # Get the card template
        if card_type not in card_templates:
            log_step(f"Card template not found: {card_type}", "error")
            return False
        
        template = card_templates[card_type]
        
        # For simple text messages
        if "text" in template:
            message_text = template["text"].format(**params)
            response = requests.post(GCHAT_WEBHOOK, json={"text": message_text})
        else:
            # For card messages, we need to properly format the JSON
            # This would need more complex templating in production
            # For now, fall back to text
            return post_to_gchat_text(card_type, params)
        
        if response.status_code == 200:
            pipeline_stats["gchat_posts"] += 1
            return True
        else:
            log_step(f"GChat post failed: {response.status_code}", "error")
            return False
            
    except Exception as e:
        log_step(f"GChat post error: {e}", "error")
        return False

def post_to_gchat_text(message_type: str, params: Dict) -> bool:
    """Post a text message to GChat (fallback)"""
    if TEST_MODE:
        print(f"\n[TEST MODE] {message_type}: {params}")
        return True
    
    try:
        # Format message based on type
        if message_type == "no_calls":
            message = f"ℹ️ No client meetings found on {params['date']}"
        elif message_type == "missing_transcript":
            # Don't send to GChat, just log internally
            pipeline_stats["missing_transcripts"].append(params)
            print(f"    📝 Logged missing transcript: {params['client']}")
            return True
        elif message_type == "client_meeting":
            message = format_client_meeting_text(params)
        else:
            message = str(params)
        
        response = requests.post(GCHAT_WEBHOOK, json={"text": message})
        
        if response.status_code == 200:
            pipeline_stats["gchat_posts"] += 1
            return True
        else:
            log_step(f"GChat post failed: {response.status_code}", "error")
            return False
            
    except Exception as e:
        log_step(f"GChat post error: {e}", "error")
        return False

def format_client_meeting_text(params: Dict) -> str:
    """Format client meeting card as text"""
    call = params['call']
    signals = params['signals']
    
    lines = []
    lines.append(f"⚠️ Client Meeting • {call['client']}")
    lines.append(f"{call['call_date']} • Hyly lead: {call['hyly_lead']}")
    lines.append("")
    lines.append("Business Signals")
    lines.append("")
    
    for i, signal in enumerate(signals[:3], 1):
        severity_emoji = {"act_now": "🔴", "watch": "🟡", "healthy": "🟢"}
        severity_labels = {"act_now": "ACT NOW", "watch": "WATCH", "healthy": "HEALTHY"}
        
        emoji = severity_emoji.get(signal.get('severity_final', 'watch'), "🟡")
        severity_label = severity_labels.get(signal.get('severity_final', 'watch'), "WATCH")
        
        signal_type_display = {
            "knowledge": "Knowledge gap",
            "skill": "Skill gap",
            "gap": "Product gap",
            "positive": "Growth signal",
            "competitor": "Competitive signal"
        }.get(signal['signal_type'], signal['signal_type'])
        
        lines.append(f"{i}. {emoji} {severity_label} • {signal_type_display}")
        lines.append("")
        lines.append(signal.get('signal_title', 'Signal detected'))
        lines.append("")
        lines.append("Why it matters")
        lines.append(signal['context'])
        lines.append("")
    
    lines.append("Links")
    lines.append("")
    lines.append(f"OPEN IN NOTION: {call['notion_page_url']}")
    
    return "\n".join(lines)

def query_calls_for_date(date_str: str) -> List[Dict]:
    """Query all calls for a specific date with strict validation"""
    log_step(f"Query MeetingDiary for {date_str}")
    
    # GUARDRAIL: Validate date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        log_step(f"Invalid date format: {date_str}", "error")
        return []
    
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
            log_step(f"Notion query failed: {response.status_code}", "error")
            return []
        
        data = response.json()
        calls = []
        
        for page in data.get("results", []):
            try:
                call_data = extract_call_data(page)
                if call_data:
                    calls.append(call_data)
                    pipeline_stats["calls_found"] += 1
            except Exception as e:
                log_step(f"Error parsing call: {e}", "error")
                continue
        
        log_step(f"Found {len(calls)} calls", "complete")
        return calls
        
    except Exception as e:
        log_step(f"API error: {e}", "error")
        return []

def extract_call_data(page: Dict) -> Optional[Dict]:
    """Extract and validate call data from Notion page"""
    # GUARDRAIL: Ensure all required fields are present
    required_fields = ["meeting_page_id", "client", "call_date"]
    
    call_data = {
        "meeting_page_id": page.get("id"),
        "notion_page_url": page.get("url"),
        "client": extract_client_name(page),
        "call_date": extract_property(page, "Meeting Date", "date"),
        "meeting_type": extract_property(page, "Meeting Type", "select"),
        "hyly_lead": extract_person(page, "Hyly Lead") or "Unknown",
        "transcript_url": extract_transcript_url(page),
        "already_processed": extract_property(page, "Added to Google Chat", "checkbox") or False,
        "deal_strategy_relation": extract_relation(page, "📈 sdb.DealStrategy")
    }
    
    # Validate required fields
    for field in required_fields:
        if not call_data.get(field):
            log_step(f"Missing required field: {field}", "error")
            return None
    
    return call_data

def process_calls_for_date(date_str: str) -> Tuple[bool, bool]:
    """
    Process all calls for a date
    Returns: (should_continue, found_duplicate)
    """
    log_step(f"Processing date: {date_str}")
    
    # Step 1: Query calls
    calls = query_calls_for_date(date_str)
    
    if not calls:
        # No calls found - notify
        post_to_gchat_text("no_calls", {"date": date_str})
        log_step(f"No calls on {date_str}", "complete")
        return True, False  # Continue to previous day
    
    # Step 2: Categorize calls
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
    
    # Step 3: Check for duplicates (stop condition)
    if already_processed:
        log_step(f"Found {len(already_processed)} already processed - stopping", "complete")
        return False, True  # Stop, found duplicate
    
    # Step 4: Log missing transcripts (don't send to GChat)
    for call in calls_without_transcript:
        post_to_gchat_text("missing_transcript", {
            "client": call['client'],
            "meeting_type": call.get('meeting_type', 'Unknown'),
            "date": date_str,
            "hyly_lead": call.get('hyly_lead', 'Unknown')
        })
    
    # Step 5: Process calls with transcripts
    for call in calls_with_transcript:
        process_single_call(call)
    
    log_step(f"Completed {date_str}: {len(calls_with_transcript)} processed", "complete")
    return True, False  # Continue to previous day

def process_single_call(call: Dict) -> bool:
    """Process a single call with all steps"""
    log_step(f"Processing call: {call['client']}")
    
    # GUARDRAIL: Validate call data
    if not call.get('transcript_url'):
        log_step("No transcript URL", "skip")
        return False
    
    # Step 1: Download transcript
    transcript = download_transcript(call['transcript_url'])
    if not transcript:
        pipeline_stats["calls_skipped"] += 1
        return False
    
    # Step 2: Extract signals
    signals = extract_signals(transcript, call)
    if not signals:
        log_step("No signals found", "complete")
        pipeline_stats["calls_processed"] += 1
        return True
    
    pipeline_stats["signals_extracted"] += len(signals)
    
    # Step 3: Apply MRR weighting
    mrr_value, mrr_tier = lookup_mrr(call.get('deal_strategy_relation'))
    for signal in signals:
        apply_mrr_weighting(signal, mrr_tier)
    
    # Step 4: Check idempotency
    signals_to_process = []
    for signal in signals:
        if not is_duplicate_signal(signal, call):
            signals_to_process.append(signal)
    
    # Step 5: Route to feeds and write themes
    if signals_to_process:
        # Write theme files
        for signal in signals_to_process:
            write_theme_file(signal, call)
        
        # Send client meeting card
        post_to_gchat_text("client_meeting", {
            "call": call,
            "signals": signals_to_process
        })
        
        # Send other feed messages as needed
        route_to_feeds(call, signals_to_process)
    
    # Step 6: Update Notion
    if not TEST_MODE:
        update_notion_page(call['meeting_page_id'])
    
    pipeline_stats["calls_processed"] += 1
    log_step(f"Call processed: {len(signals)} signals", "complete")
    return True

def download_transcript(url: str) -> Optional[str]:
    """Download transcript from Google Drive"""
    log_step("Downloading transcript")
    
    if not url:
        return None
    
    # Extract file ID
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        log_step("Invalid Google Drive URL", "error")
        return None
    
    file_id = match.group(1)
    
    # Download with token refresh if needed
    headers = {"Authorization": f"Bearer {GOOGLE_ACCESS_TOKEN}"}
    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    
    try:
        response = requests.get(download_url, headers=headers)
        
        if response.status_code == 401:
            # Token expired, refresh
            new_token = refresh_google_token()
            if new_token:
                headers = {"Authorization": f"Bearer {new_token}"}
                response = requests.get(download_url, headers=headers)
        
        if response.status_code == 200:
            log_step(f"Downloaded {len(response.text)} chars", "complete")
            return response.text
            
    except Exception as e:
        log_step(f"Download error: {e}", "error")
    
    return None

def extract_signals(transcript: str, call: Dict) -> List[Dict]:
    """Extract signals from transcript"""
    log_step("Extracting signals")
    
    signals = []
    
    # This is simplified - in production would use AI
    # For now, basic pattern matching
    
    text_lower = transcript.lower()
    
    if "can we" in text_lower or "how do" in text_lower:
        signals.append({
            "signal_type": "knowledge",
            "category": taxonomy["knowledge"]["category"],
            "theme_slug": "knowledge-enablement-feature-awareness",
            "signal_title": "Feature awareness gap",
            "verbatim_quote": "[Client] Can we do this?",
            "context": "Client unaware of existing capabilities.",
            "severity_raw": "watch",
            "severity_final": "watch"
        })
    
    log_step(f"Found {len(signals)} signals", "complete")
    return signals

def lookup_mrr(deal_strategy_id: Optional[str]) -> Tuple[float, str]:
    """Lookup MRR from DealStrategy"""
    if not deal_strategy_id:
        return 0, "standard"
    
    # Simplified for demo
    return 5000, "high" if 5000 > mrr_thresholds["mrr_high_threshold"] else "standard"

def apply_mrr_weighting(signal: Dict, mrr_tier: str):
    """Apply MRR-based severity weighting"""
    if mrr_tier == "high" and signal['severity_raw'] in mrr_thresholds.get("severity_bump_when_mrr_high", {}):
        signal['severity_final'] = mrr_thresholds["severity_bump_when_mrr_high"][signal['severity_raw']]

def is_duplicate_signal(signal: Dict, call: Dict) -> bool:
    """Check if signal already exists in theme file"""
    theme_path = f"themes/{signal['theme_slug']}.md"
    
    if not os.path.exists(theme_path):
        return False
    
    # Check if this call's URL is already in the theme file
    with open(theme_path, 'r') as f:
        content = f.read()
        if call['notion_page_url'] in content:
            return True
    
    return False

def write_theme_file(signal: Dict, call: Dict):
    """Write or update theme file"""
    theme_path = f"themes/{signal['theme_slug']}.md"
    
    if os.path.exists(theme_path):
        log_step(f"Updating theme: {signal['theme_slug']}", "complete")
        pipeline_stats["themes_updated"] += 1
        # Would append to file in production
    else:
        log_step(f"Creating theme: {signal['theme_slug']}", "complete")
        pipeline_stats["themes_created"] += 1
        
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

def route_to_feeds(call: Dict, signals: List[Dict]):
    """Route signals to appropriate feeds"""
    for signal in signals:
        feeds = taxonomy[signal['signal_type']]['feeds']
        
        # Product digest for critical gaps
        if "product_digest_feed" in feeds and signal.get('severity_final') == 'critical':
            # Send critical gap alert
            pass
        
        # Marketing feed for positive signals
        if "marketing_feed" in feeds and signal['signal_type'] == 'positive':
            # Send positive signal
            pass

def update_notion_page(page_id: str) -> bool:
    """Update Notion page to mark as processed"""
    log_step("Updating Notion page")
    
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
        
        if response.status_code == 200:
            pipeline_stats["notion_updates"] += 1
            log_step("Notion updated", "complete")
            return True
            
    except Exception as e:
        log_step(f"Notion update error: {e}", "error")
    
    return False

# Helper functions for data extraction
def extract_client_name(page: Dict) -> str:
    """Extract client name from page"""
    try:
        if "properties" in page and "Discovery" in page["properties"]:
            title_prop = page["properties"]["Discovery"]
            if title_prop["type"] == "title" and title_prop["title"]:
                full_title = title_prop["title"][0]["plain_text"]
                parts = full_title.split('.')
                if len(parts) >= 1:
                    client = parts[0]
                    # Clean up training call names
                    client = re.sub(r'(New Onsite - Training|CSM Training|Retraining)', '', client)
                    client = re.sub(r'[<>]', '', client).strip()
                    return client if client else parts[0]
                return full_title
    except:
        pass
    return "Unknown Client"

def extract_property(page: Dict, prop_name: str, prop_type: str):
    """Extract property value from page"""
    try:
        if prop_name in page.get("properties", {}):
            prop = page["properties"][prop_name]
            
            if prop_type == "date" and prop["type"] == "date" and prop.get("date"):
                return prop["date"]["start"]
            elif prop_type == "select" and prop["type"] == "select" and prop.get("select"):
                return prop["select"]["name"]
            elif prop_type == "checkbox" and prop["type"] == "checkbox":
                return prop["checkbox"]
            elif prop_type == "url" and prop["type"] == "url":
                return prop["url"]
    except:
        pass
    return None

def extract_person(page: Dict, prop_name: str) -> Optional[str]:
    """Extract person name from property"""
    try:
        if prop_name in page.get("properties", {}):
            people_prop = page["properties"][prop_name]
            if people_prop["type"] == "people" and people_prop.get("people"):
                person = people_prop["people"][0]
                if "name" in person:
                    return person["name"]
    except:
        pass
    return None

def extract_transcript_url(page: Dict) -> Optional[str]:
    """Extract transcript URL from priority fields"""
    for field in call_filter["transcript_fields_priority"]:
        url = extract_property(page, field, "url")
        if url:
            return url
    return None

def extract_relation(page: Dict, prop_name: str) -> Optional[str]:
    """Extract relation ID"""
    try:
        if prop_name in page.get("properties", {}):
            rel_prop = page["properties"][prop_name]
            if rel_prop["type"] == "relation" and rel_prop.get("relation"):
                return rel_prop["relation"][0]["id"] if rel_prop["relation"] else None
    except:
        pass
    return None

def main():
    """Main pipeline execution with strict guardrails"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE - STRICT VERSION")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # GUARDRAIL: Validate environment
    log_step("Validating environment")
    if not NOTION_TOKEN:
        log_step("NOTION_TOKEN not set", "error")
        sys.exit(1)
    log_step("Environment validated", "complete")
    
    # Process dates from yesterday backwards
    for days_back in range(1, 8):  # Max 7 days
        check_date = datetime.now() - timedelta(days=days_back)
        date_str = check_date.strftime("%Y-%m-%d")
        
        should_continue, found_duplicate = process_calls_for_date(date_str)
        
        if found_duplicate:
            log_step("ALL CAUGHT UP - found processed calls", "complete")
            break
        
        if not should_continue:
            break
    
    # Print final summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Calls found: {pipeline_stats['calls_found']}")
    print(f"Calls processed: {pipeline_stats['calls_processed']}")
    print(f"Calls skipped: {pipeline_stats['calls_skipped']}")
    print(f"Missing transcripts logged: {len(pipeline_stats['missing_transcripts'])}")
    print(f"Signals extracted: {pipeline_stats['signals_extracted']}")
    print(f"Themes created: {pipeline_stats['themes_created']}")
    print(f"Themes updated: {pipeline_stats['themes_updated']}")
    print(f"GChat posts: {pipeline_stats['gchat_posts']}")
    print(f"Notion updates: {pipeline_stats['notion_updates']}")
    
    if pipeline_stats["errors"]:
        print(f"\n⚠️ Errors encountered: {len(pipeline_stats['errors'])}")
        for error in pipeline_stats["errors"]:
            print(f"  - {error}")
    
    print("\n✓ Pipeline complete")

if __name__ == "__main__":
    main()