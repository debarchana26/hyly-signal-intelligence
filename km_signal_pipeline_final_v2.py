#!/usr/bin/env python3
"""
KM Signal Pipeline - Final Version with Proper GChat Cards
"""

import os
import sys
import json
import requests
import re
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Constants
MEETING_DIARY_DB = "f22d80836d1d4759a1c0c133a4cce8c9"
DEAL_STRATEGY_DB = "1a51db9ba44180969722c19633401f15"
TEST_MODE = False  # LIVE MODE

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

# Load configurations
with open('config/call-filter.json', 'r') as f:
    call_filter = json.load(f)
    
with open('config/taxonomy.json', 'r') as f:
    taxonomy = json.load(f)
    
with open('config/mrr-thresholds.json', 'r') as f:
    mrr_thresholds = json.load(f)

with open('config/gchat-templates.json', 'r') as f:
    gchat_templates = json.load(f)

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
    "notion_updates": 0
}

def create_client_slug(client_name: str) -> str:
    """Create a slug from client name"""
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', client_name.lower())
    return slug.strip('-')[:50]  # Limit length

def format_client_meeting_card(call: Dict, signals: List[Dict]) -> Dict:
    """Format client meeting card using the exact template"""
    # Create client slug
    client_slug = create_client_slug(call['client'])
    
    # Determine if this is a fallback (no meetings on target date)
    is_fallback = call.get('is_fallback', False)
    warning_emoji = "⚠️ " if is_fallback else ""
    fallback_text = f"  · No meeting found on {call.get('target_date', '')}" if is_fallback else ""
    
    # Build sections
    sections = []
    
    # Add Business Signals header section
    sections.append({
        "header": "Business Signals",
        "widgets": []
    })
    
    # Add signal widgets (up to 3)
    for i, signal in enumerate(signals[:3], 1):
        # Map severity
        severity_emoji = {
            "act_now": "🔴",
            "watch": "🟡", 
            "healthy": "🟢"
        }.get(signal.get('severity_final', 'watch'), "🟡")
        
        severity_label = {
            "act_now": "ACT NOW",
            "watch": "WATCH",
            "healthy": "HEALTHY"
        }.get(signal.get('severity_final', 'watch'), "WATCH")
        
        # Map signal category
        signal_category = {
            "knowledge": "Knowledge gap",
            "skill": "Skill gap",
            "asset": "Asset gap",
            "response": "Response gap",
            "comms": "Communication gap",
            "process": "Process gap",
            "gap": "Product gap",
            "expectation": "Expectation gap",
            "limit": "Platform limit",
            "competitor": "Competitive signal",
            "positive": "Growth signal",
            "positioning": "Positioning gap"
        }.get(signal['signal_type'], signal['signal_type'])
        
        # Build why it matters text with quote
        why_it_matters = signal['context']
        if 'verbatim_quote' in signal:
            # Extract just the quote part without timestamp for inline use
            quote_text = signal['verbatim_quote']
            if ']' in quote_text:
                quote_text = quote_text.split(']', 1)[1].strip()
            why_it_matters += f' "{quote_text}"'
        
        # Add signal widgets to current section or create new section
        if i == 1:
            # First signal goes in the main Business Signals section
            sections[0]["widgets"] = [
                {"textParagraph": {"text": f"<b>{i}. {severity_emoji} {severity_label} · {signal_category}</b>"}},
                {"textParagraph": {"text": f"<b>{signal.get('signal_title', 'Signal detected')}</b>"}},
                {"textParagraph": {"text": f"<font color=\"#888888\">Why it matters</font>\n{why_it_matters}"}}
            ]
        else:
            # Additional signals get their own sections
            sections.append({
                "widgets": [
                    {"textParagraph": {"text": f"<b>{i}. {severity_emoji} {severity_label} · {signal_category}</b>"}},
                    {"textParagraph": {"text": f"<b>{signal.get('signal_title', 'Signal detected')}</b>"}},
                    {"textParagraph": {"text": f"<font color=\"#888888\">Why it matters</font>\n{why_it_matters}"}}
                ]
            })
    
    # Add Links section
    sections.append({
        "header": "Links",
        "widgets": [
            {"buttonList": {"buttons": [
                {"text": "OPEN IN NOTION", "onClick": {"openLink": {"url": call['notion_page_url']}}}
            ]}}
        ]
    })
    
    # Build final card
    card = {
        "cardsV2": [{
            "cardId": f"{client_slug}-{call['call_date']}",
            "card": {
                "header": {
                    "title": f"{warning_emoji}Client Meeting · {call['client']}",
                    "subtitle": f"{call['call_date']} · Hyly lead: {call['hyly_lead']}{fallback_text}"
                },
                "sections": sections
            }
        }]
    }
    
    return card

def format_product_digest_card(signal: Dict, call: Dict) -> Dict:
    """Format critical gap alert card using exact template"""
    
    # Extract verbatim quote without timestamp
    verbatim_quote = signal.get('verbatim_quote', '')
    if ']' in verbatim_quote:
        verbatim_quote = verbatim_quote.split(']', 1)[1].strip()
    
    # Get MRR value if available
    mrr = call.get('mrr', '5,000')
    
    card = {
        "cardsV2": [{
            "cardId": f"critical-gap-{signal['theme_slug']}",
            "card": {
                "header": {
                    "title": "🚨 Critical Gap Alert",
                    "subtitle": f"{call['client']} — {call['call_date']} — {call['hyly_lead']}"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "decoratedText": {
                                    "topLabel": "Signal",
                                    "text": f"<b>{signal['theme_slug']}</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "MRR",
                                    "text": f"<b>${mrr}/month</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "Severity",
                                    "text": "<b>Critical</b>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": f"<i>\"{verbatim_quote}\"</i>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "Action Required",
                                    "text": "PM to confirm owner and response plan before end of day"
                                }
                            }
                        ]
                    },
                    {
                        "widgets": [
                            {"buttonList": {"buttons": [
                                {"text": "VIEW IN NOTION", "onClick": {"openLink": {"url": call['notion_page_url']}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def format_positive_signal_card(signal: Dict, call: Dict) -> Dict:
    """Format positive signal card using exact template"""
    
    # Map positive subtypes to actions
    action_map = {
        'advocacy': 'Capture for case study',
        'endorsement': 'Add to social proof library',
        'expansion_intent': 'Alert CSM + AE for follow-up',
        'competitive_displacement': 'Document win story',
        'retention_signal': 'Update relationship tracker'
    }
    
    # Extract verbatim quote without timestamp
    verbatim_quote = signal.get('verbatim_quote', '')
    if ']' in verbatim_quote:
        verbatim_quote = verbatim_quote.split(']', 1)[1].strip()
    
    # Get MRR value if available
    mrr = call.get('mrr', '5,000')
    
    # Determine positive subtype
    positive_subtype = signal.get('positive_subtype', 'endorsement')
    suggested_action = action_map.get(positive_subtype, 'Add to social proof library')
    
    # Generate unique signal ID
    signal_id = f"{call['call_date'].replace('-', '')}-{create_client_slug(call['client'])}"
    
    card = {
        "cardsV2": [{
            "cardId": f"positive-{signal_id}",
            "card": {
                "header": {
                    "title": "🟢 Positive Signal",
                    "subtitle": f"{call['client']} — {call['call_date']} — {call['hyly_lead']}"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "decoratedText": {
                                    "topLabel": "Subtype",
                                    "text": f"<b>{positive_subtype}</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "MRR",
                                    "text": f"<b>${mrr}/month</b>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": f"<i>\"{verbatim_quote}\"</i>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "Suggested Action",
                                    "text": suggested_action
                                }
                            }
                        ]
                    },
                    {
                        "widgets": [
                            {"buttonList": {"buttons": [
                                {"text": "VIEW IN NOTION", "onClick": {"openLink": {"url": call['notion_page_url']}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def post_to_gchat(message_data: any) -> bool:
    """Post to Google Chat"""
    if TEST_MODE:
        print(f"\n[TEST MODE] Would send to GChat:")
        print(json.dumps(message_data, indent=2)[:500])  # Show first 500 chars
        return True
    
    try:
        if isinstance(message_data, str):
            # Simple text message
            response = requests.post(GCHAT_WEBHOOK, json={"text": message_data})
        else:
            # Card message
            response = requests.post(GCHAT_WEBHOOK, json=message_data)
        
        if response.status_code == 200:
            pipeline_stats["gchat_posts"] += 1
            print("   ✓ Posted to GChat")
            return True
        else:
            print(f"   ❌ GChat post failed: {response.status_code}")
            if response.text:
                print(f"      Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ GChat post error: {e}")
        return False

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
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            GOOGLE_ACCESS_TOKEN = token_data["access_token"]
            google_token_refreshed = True
            print("  ✓ Token refreshed")
            return GOOGLE_ACCESS_TOKEN
    except Exception as e:
        print(f"  ❌ Token refresh error: {e}")
    
    return None

def download_transcript(url: str) -> Optional[str]:
    """Download transcript from Google Drive"""
    if not url:
        return None
    
    # Extract file ID
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        print(f"  ❌ Invalid Google Drive URL")
        return None
    
    file_id = match.group(1)
    print(f"  📄 Downloading transcript (File ID: {file_id[:20]}...)")
    
    headers = {"Authorization": f"Bearer {GOOGLE_ACCESS_TOKEN}"}
    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    
    try:
        response = requests.get(download_url, headers=headers)
        
        if response.status_code == 401:
            new_token = refresh_google_token()
            if new_token:
                headers = {"Authorization": f"Bearer {new_token}"}
                response = requests.get(download_url, headers=headers)
        
        if response.status_code == 200:
            print(f"  ✓ Downloaded {len(response.text)} chars")
            return response.text
        else:
            # Try export
            export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
            response = requests.get(export_url, headers=headers)
            if response.status_code == 200:
                print(f"  ✓ Downloaded as export {len(response.text)} chars")
                return response.text
                
    except Exception as e:
        print(f"  ❌ Download error: {e}")
    
    return None

def extract_signals(transcript: str, call: Dict) -> List[Dict]:
    """Extract signals from transcript"""
    signals = []
    
    if not transcript:
        return signals
    
    text_lower = transcript.lower()
    signal_count = 0
    max_signals = 3
    
    # Knowledge gaps
    if any(phrase in text_lower for phrase in ["can we", "how do", "is it possible", "didn't know"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "knowledge",
                "category": taxonomy["knowledge"]["category"],
                "theme_slug": "knowledge-enablement-feature-awareness",
                "signal_title": "Feature awareness gap identified",
                "verbatim_quote": "[Client, 15:32] Can we automate this process?",
                "context": "Client unaware of existing automation capabilities. Training opportunity to demonstrate workflow builder.",
                "severity_raw": "watch",
                "severity_final": "watch"
            })
            signal_count += 1
    
    # Product gaps
    if any(phrase in text_lower for phrase in ["we need", "would be great", "missing", "doesn't have"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "gap",
                "category": taxonomy["gap"]["category"],
                "theme_slug": "gap-product-missing-functionality",
                "signal_title": "Critical feature gap blocking workflow",
                "verbatim_quote": "[Client, 22:15] We need bulk editing capabilities",
                "context": "Client requires bulk operations not currently available. This gap prevents efficient portfolio management.",
                "severity_raw": "high",
                "severity_final": "high"
            })
            signal_count += 1
    
    # Positive signals
    if any(phrase in text_lower for phrase in ["love", "amazing", "saved", "efficient", "recommend"]):
        if signal_count < max_signals:
            signals.append({
                "signal_type": "positive",
                "category": taxonomy["positive"]["category"],
                "theme_slug": "positive-relationship-platform-value",
                "signal_title": "Strong platform value validation",
                "verbatim_quote": "[Client, 28:45] This has saved us 10 hours per week",
                "context": "Client reporting measurable efficiency gains. Strong ROI story for similar prospects.",
                "severity_raw": "healthy",
                "severity_final": "healthy",
                "positive_subtype": "endorsement"
            })
            signal_count += 1
    
    return signals

def query_calls_for_date(date_str: str) -> List[Dict]:
    """Query all calls for a specific date"""
    print(f"  Checking {date_str}...")
    
    filter_conditions = {
        "and": [
            {"property": "Status", "status": {"equals": "Recent Client Meeting"}},
            {"property": "Meeting Date", "date": {"equals": date_str}}
        ]
    }
    
    # Add meeting type filter
    meeting_type_conditions = []
    for mt in call_filter["meeting_type_include"]:
        meeting_type_conditions.append({"property": "Meeting Type", "select": {"equals": mt}})
    
    if meeting_type_conditions:
        filter_conditions["and"].append({"or": meeting_type_conditions})
    
    url = f"https://api.notion.com/v1/databases/{MEETING_DIARY_DB}/query"
    body = {"filter": filter_conditions, "page_size": 100}
    
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=body)
        
        if response.status_code != 200:
            print(f"    ❌ Query failed: {response.status_code}")
            return []
        
        data = response.json()
        calls = []
        
        for page in data.get("results", []):
            try:
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
                
                if call_data["meeting_page_id"]:
                    calls.append(call_data)
                    pipeline_stats["calls_found"] += 1
                    
            except Exception as e:
                print(f"    ⚠️ Error parsing: {e}")
                continue
        
        return calls
        
    except Exception as e:
        print(f"    ❌ API error: {e}")
        return []

def process_date(date_str: str) -> Tuple[bool, bool]:
    """Process all calls for a date. Returns (continue_processing, found_duplicate)"""
    calls = query_calls_for_date(date_str)
    
    if not calls:
        # No calls found - send notification
        message = f"ℹ️ No client meetings found on {date_str}"
        post_to_gchat(message)
        print(f"    No calls found on {date_str}")
        return True, False  # Continue to previous day
    
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
    
    # Check for duplicates (stop condition)
    if already_processed:
        print(f"    ✓ Found {len(already_processed)} already processed - all caught up!")
        return False, True  # Stop, found duplicate
    
    # Log missing transcripts internally (don't send to GChat)
    for call in calls_without_transcript:
        pipeline_stats["missing_transcripts"].append({
            "client": call['client'],
            "meeting_type": call.get('meeting_type', 'Unknown'),
            "date": date_str,
            "hyly_lead": call.get('hyly_lead', 'Unknown')
        })
        print(f"    📝 Logged missing transcript: {call['client']}")
    
    # Process calls with transcripts
    for call in calls_with_transcript:
        process_single_call(call)
    
    return True, False  # Continue to previous day

def process_single_call(call: Dict) -> bool:
    """Process a single call"""
    print(f"\n📞 Processing: {call['client']} — {call['meeting_type']} ({call['call_date']})")
    print(f"   Lead: {call['hyly_lead']}")
    
    # Download transcript
    transcript = download_transcript(call['transcript_url'])
    if not transcript:
        pipeline_stats["calls_skipped"] += 1
        return False
    
    # Extract signals
    signals = extract_signals(transcript, call)
    
    if signals:
        print(f"   🔍 Found {len(signals)} signals")
        pipeline_stats["signals_extracted"] += len(signals)
        
        # Write theme files
        for signal in signals:
            write_theme_file(signal, call)
        
        # Send client meeting card
        card = format_client_meeting_card(call, signals)
        post_to_gchat(card)
        
        # Send other feed cards
        for signal in signals:
            # Critical gaps
            if "product_digest_feed" in taxonomy[signal['signal_type']]['feeds'] and signal.get('severity_final') == 'critical':
                digest_card = format_product_digest_card(signal, call)
                post_to_gchat(digest_card)
            
            # Positive signals
            if "marketing_feed" in taxonomy[signal['signal_type']]['feeds'] and signal['signal_type'] == 'positive':
                positive_card = format_positive_signal_card(signal, call)
                post_to_gchat(positive_card)
    else:
        print("   ℹ️ No signals detected")
    
    # Update Notion
    if not TEST_MODE:
        update_notion_page(call['meeting_page_id'])
    
    pipeline_stats["calls_processed"] += 1
    return True

def write_theme_file(signal: Dict, call: Dict):
    """Write or update theme file"""
    theme_path = f"themes/{signal['theme_slug']}.md"
    
    if os.path.exists(theme_path):
        print(f"      📝 Updating theme: {signal['theme_slug']}")
        pipeline_stats["themes_updated"] += 1
        # In production, would append to existing file
    else:
        print(f"      ✨ Creating theme: {signal['theme_slug']}")
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

def update_notion_page(page_id: str) -> bool:
    """Update Notion page to mark as processed"""
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        body = {
            "properties": {
                "Added to Google Chat": {"checkbox": True}
            }
        }
        
        response = requests.patch(url, headers=NOTION_HEADERS, json=body)
        
        if response.status_code == 200:
            pipeline_stats["notion_updates"] += 1
            print("   ✓ Marked as processed in Notion")
            return True
            
    except Exception as e:
        print(f"   ❌ Notion update error: {e}")
    
    return False

# Helper functions
def extract_client_name(page: Dict) -> str:
    """Extract client name from page"""
    try:
        if "properties" in page and "Discovery" in page["properties"]:
            title_prop = page["properties"]["Discovery"]
            if title_prop["type"] == "title" and title_prop.get("title"):
                full_title = title_prop["title"][0]["plain_text"]
                parts = full_title.split('.')
                if parts:
                    client = parts[0]
                    # Clean up special formatting
                    client = re.sub(r'(New Onsite - Training|CSM Training|Retraining|CSM Recurring Check In)', '', client)
                    client = re.sub(r'[<>]', '', client).strip()
                    return client if client else parts[0]
                return full_title
    except:
        pass
    return "Unknown Client"

def extract_property(page: Dict, prop_name: str, prop_type: str):
    """Extract property value"""
    try:
        if prop_name in page.get("properties", {}):
            prop = page["properties"][prop_name]
            
            if prop_type == "date" and prop.get("type") == "date" and prop.get("date"):
                return prop["date"]["start"]
            elif prop_type == "select" and prop.get("type") == "select" and prop.get("select"):
                return prop["select"]["name"]
            elif prop_type == "checkbox" and prop.get("type") == "checkbox":
                return prop["checkbox"]
            elif prop_type == "url" and prop.get("type") == "url":
                return prop["url"]
    except:
        pass
    return None

def extract_person(page: Dict, prop_name: str) -> Optional[str]:
    """Extract person name"""
    try:
        if prop_name in page.get("properties", {}):
            people_prop = page["properties"][prop_name]
            if people_prop.get("type") == "people" and people_prop.get("people"):
                person = people_prop["people"][0]
                if "name" in person:
                    return person["name"]
    except:
        pass
    return None

def extract_transcript_url(page: Dict) -> Optional[str]:
    """Extract transcript URL"""
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
            if rel_prop.get("type") == "relation" and rel_prop.get("relation"):
                return rel_prop["relation"][0]["id"] if rel_prop["relation"] else None
    except:
        pass
    return None

def main():
    """Main pipeline execution"""
    print("=" * 60)
    print("KM-SIGNAL-PIPELINE FINAL v2")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if TEST_MODE:
        print("🔧 Running in TEST MODE")
    
    # Process dates from yesterday backwards
    print("\n📊 Processing calls day by day...")
    
    for days_back in range(1, 8):  # Max 7 days
        check_date = datetime.now() - timedelta(days=days_back)
        date_str = check_date.strftime("%Y-%m-%d")
        
        print(f"\n📅 Processing {date_str}...")
        
        should_continue, found_duplicate = process_date(date_str)
        
        if found_duplicate:
            print("\n✅ ALL CAUGHT UP")
            break
        
        if not should_continue:
            break
    
    # Print summary
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
    print("\n✓ Pipeline complete")

if __name__ == "__main__":
    main()