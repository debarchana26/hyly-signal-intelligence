#!/usr/bin/env python3
"""
Weekly Product Digest - Aggregates signals from the past week
"""

import os
import json
import requests
from datetime import datetime, timedelta
import re

# Constants
TEST_MODE = False  # Set to False to actually post to GChat

# GChat Webhook
GCHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAyF9D3W8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U"

# Load taxonomy
with open('config/taxonomy.json', 'r') as f:
    taxonomy = json.load(f)

def parse_theme_file(filepath):
    """Parse a theme file to extract metadata and occurrences"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract frontmatter
    theme_data = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            frontmatter = parts[1].strip()
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    theme_data[key.strip()] = value.strip()
    
    # Extract occurrences from table
    occurrences = []
    lines = content.split('\n')
    in_table = False
    
    for line in lines:
        if '| Client | Date | Notion Page | Quote | Timestamp |' in line:
            in_table = True
            continue
        if in_table and line.startswith('|') and not line.startswith('|---'):
            # Parse table row
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first and last
            if len(parts) >= 5:
                occurrence = {
                    'client': parts[0],
                    'date': parts[1],
                    'notion_url': re.search(r'\((https://[^\)]+)\)', parts[2]).group(1) if '(' in parts[2] else '',
                    'quote': parts[3].strip('"'),
                    'timestamp': parts[4]
                }
                occurrences.append(occurrence)
    
    theme_data['occurrences'] = occurrences
    return theme_data

def get_week_signals():
    """Get all signals from the past week"""
    week_ago = datetime.now() - timedelta(days=7)
    
    # Product-related signal types
    product_signals = ['gap', 'expectation', 'limit']
    
    all_signals = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }
    
    # Scan theme files
    themes_dir = 'themes'
    for filename in os.listdir(themes_dir):
        if filename.endswith('.md') and not filename.startswith('.'):
            filepath = os.path.join(themes_dir, filename)
            theme_data = parse_theme_file(filepath)
            
            # Check if it's a product signal
            signal_type = theme_data.get('signal_type', '')
            if signal_type not in product_signals:
                continue
            
            # Check for recent occurrences
            recent_occurrences = []
            for occurrence in theme_data.get('occurrences', []):
                try:
                    occ_date = datetime.strptime(occurrence['date'], '%Y-%m-%d')
                    if occ_date >= week_ago:
                        recent_occurrences.append(occurrence)
                except:
                    continue
            
            if recent_occurrences:
                # Determine severity (simplified - in real pipeline would use MRR weighting)
                severity = 'high' if signal_type == 'gap' else 'medium'
                if theme_data.get('client_count', '1').isdigit() and int(theme_data.get('client_count', '1')) >= 3:
                    severity = 'critical'
                
                signal_info = {
                    'theme_slug': theme_data.get('theme_slug', filename[:-3]),
                    'signal_type': signal_type,
                    'category': theme_data.get('category', 'product'),
                    'status': theme_data.get('status', 'candidate'),
                    'client_count': len(set(occ['client'] for occ in recent_occurrences)),
                    'total_occurrences': len(recent_occurrences),
                    'recent_occurrences': recent_occurrences,
                    'description': extract_description(filepath)
                }
                
                all_signals[severity].append(signal_info)
    
    return all_signals

def extract_description(filepath):
    """Extract the description from theme file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    # Get first paragraph as description
    lines = content.split('\n')
    for line in lines:
        if line.strip() and not line.startswith('#'):
            return line.strip()
    
    return "Signal detected"

def format_weekly_digest(signals):
    """Format the weekly product digest as a GChat card"""
    
    # Header
    today = datetime.now()
    week_start = (today - timedelta(days=7)).strftime('%b %d')
    week_end = today.strftime('%b %d, %Y')
    week_id = today.strftime('%Y%m%d')
    
    # Count totals
    total_gaps = sum(len(signals[sev]) for sev in signals)
    critical_count = len(signals['critical'])
    high_count = len(signals['high'])
    
    # Build critical gaps widgets
    critical_widgets = []
    for signal in signals['critical'][:5]:  # Show top 5 critical
        # Get most recent occurrence for the quote
        recent_occ = signal['recent_occurrences'][0] if signal['recent_occurrences'] else None
        verbatim_quote = recent_occ['quote'] if recent_occ else "No quote available"
        if len(verbatim_quote) > 150:
            verbatim_quote = verbatim_quote[:147] + "..."
        
        # Get Notion URL from most recent occurrence
        notion_url = recent_occ['notion_url'] if recent_occ else "https://notion.so"
        
        # Get description/summary (1-2 lines)
        description = signal.get('description', 'Signal detected')
        if len(description) > 120:
            description = description[:117] + "..."
        
        critical_widgets.append({
            "textParagraph": {
                "text": f"<b>🔴 {signal['theme_slug']}</b>\n" +
                        f"{description}\n" +
                        f"Clients: {signal['client_count']} | Status: {signal['status']}\n" +
                        f"<i>\"{verbatim_quote}\"</i>\n" +
                        f"<a href=\"{notion_url}\">View in Notion</a>"
            }
        })
    
    if not critical_widgets:
        critical_widgets = [{"textParagraph": {"text": "No critical gaps this week"}}]
    
    # Build high priority widgets
    high_widgets = []
    for signal in signals['high'][:5]:  # Show top 5 high priority
        # Get most recent occurrence
        recent_occ = signal['recent_occurrences'][0] if signal['recent_occurrences'] else None
        notion_url = recent_occ['notion_url'] if recent_occ else "https://notion.so"
        
        # Get description/summary (1-2 lines)
        description = signal.get('description', 'Signal detected')
        if len(description) > 120:
            description = description[:117] + "..."
        
        high_widgets.append({
            "textParagraph": {
                "text": f"<b>🟡 {signal['theme_slug']}</b>\n" +
                        f"{description}\n" +
                        f"Clients: {signal['client_count']} | Status: {signal['status']}\n" +
                        f"<a href=\"{notion_url}\">View in Notion</a>"
            }
        })
    
    if not high_widgets:
        high_widgets = [{"textParagraph": {"text": "No high priority items this week"}}]
    
    # Build the card
    card = {
        "cardsV2": [{
            "cardId": f"weekly-digest-{week_id}",
            "card": {
                "header": {
                    "title": "📊 Weekly Product Digest",
                    "subtitle": f"{week_start} - {week_end}",
                    "imageUrl": "https://fonts.gstatic.com/s/i/googlematerialicons/insights/v6/24px.svg",
                    "imageType": "CIRCLE"
                },
                "sections": [
                    {
                        "header": "Summary",
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": f"<b>{total_gaps} product signals this week</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "startIcon": {
                                        "knownIcon": "BOOKMARK"
                                    },
                                    "text": f"🔴 {critical_count} Critical - Immediate PM attention required"
                                }
                            },
                            {
                                "decoratedText": {
                                    "startIcon": {
                                        "knownIcon": "CLOCK"
                                    },
                                    "text": f"🟡 {high_count} High - Address this sprint"
                                }
                            }
                        ]
                    },
                    {
                        "header": "🔴 CRITICAL GAPS",
                        "collapsible": False,
                        "widgets": critical_widgets
                    },
                    {
                        "header": "🟡 HIGH PRIORITY",
                        "collapsible": True,
                        "widgets": high_widgets
                    },
                    {
                        "widgets": [
                            {"buttonList": {"buttons": [
                                {"text": "VIEW ALL THEMES", "onClick": {"openLink": {"url": "https://github.com/debarchana26/hyly-signal-intelligence/tree/main/themes"}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def post_to_gchat(message):
    """Post message to Google Chat"""
    if TEST_MODE:
        print("\n[TEST MODE - NOT SENT] Weekly Product Digest:")
        print("=" * 60)
        if isinstance(message, dict):
            print(json.dumps(message, indent=2)[:2000])  # Show first 2000 chars
        else:
            print(message)
        print("=" * 60)
        return True
    else:
        # Send as card if it's a dict, otherwise as text
        if isinstance(message, dict):
            response = requests.post(GCHAT_WEBHOOK, json=message)
        else:
            response = requests.post(GCHAT_WEBHOOK, json={"text": message})
            
        if response.status_code == 200:
            print("✓ Weekly digest posted to GChat")
            return True
        else:
            print(f"❌ Failed to post digest: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text[:200]}")
            return False

def main():
    """Generate and post weekly product digest"""
    print("=" * 60)
    print("WEEKLY PRODUCT DIGEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'TEST' if TEST_MODE else 'LIVE'}")
    print("=" * 60)
    
    # Get signals from past week
    print("\n📊 Analyzing signals from past week...")
    signals = get_week_signals()
    
    # Count signals
    total_signals = sum(len(signals[sev]) for sev in signals)
    print(f"Found {total_signals} product signals:")
    for severity in ['critical', 'high', 'medium', 'low']:
        if signals[severity]:
            print(f"  - {severity.capitalize()}: {len(signals[severity])}")
    
    if total_signals > 0:
        # Format and post digest
        print("\n📮 Generating digest card...")
        card_message = format_weekly_digest(signals)
        
        # Post to GChat
        post_to_gchat(card_message)
    else:
        print("\nℹ️ No product signals found for the past week")
        # Send a simple text notification
        no_signals_msg = f"ℹ️ Weekly Product Digest: No product signals found for {datetime.now().strftime('%b %d')} - {(datetime.now() - timedelta(days=7)).strftime('%b %d, %Y')}"
        post_to_gchat(no_signals_msg)
    
    print("\n✓ Weekly digest complete")

if __name__ == "__main__":
    main()