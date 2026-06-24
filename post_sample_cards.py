#!/usr/bin/env python3
"""
Post sample cards to Google Chat to demonstrate all card formats
"""

import json
import requests
import time
from sample_daily_digest import (
    generate_sample_client_meeting_card,
    generate_critical_gap_alert,
    generate_positive_signal_card,
    generate_sample_weekly_digest
)

# GChat Webhook
GCHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAyF9D3W8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U"

def post_to_gchat(card_data, card_name):
    """Post a card to Google Chat"""
    try:
        print(f"📮 Posting {card_name}...")
        response = requests.post(GCHAT_WEBHOOK, json=card_data)
        
        if response.status_code == 200:
            print(f"   ✓ {card_name} posted successfully")
            return True
        else:
            print(f"   ❌ Failed to post {card_name}: {response.status_code}")
            if response.text:
                print(f"      Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Error posting {card_name}: {e}")
        return False

def main():
    print("=" * 60)
    print("POSTING SAMPLE CARDS TO GOOGLE CHAT")
    print("=" * 60)
    print("\nThis will post 4 sample cards to demonstrate all formats:\n")
    
    # Post intro message
    intro_msg = {
        "text": "🎨 *SAMPLE CARD DEMONSTRATIONS*\n\nShowing all 4 card formats used by the KM Signal Pipeline:"
    }
    post_to_gchat(intro_msg, "Intro message")
    time.sleep(2)
    
    # 1. Client Meeting Card
    print("\n1️⃣ CLIENT MEETING CARD")
    meeting_card = generate_sample_client_meeting_card()
    post_to_gchat(meeting_card, "Client Meeting Card")
    time.sleep(3)
    
    # 2. Critical Gap Alert
    print("\n2️⃣ CRITICAL GAP ALERT")
    critical_card = generate_critical_gap_alert()
    post_to_gchat(critical_card, "Critical Gap Alert")
    time.sleep(3)
    
    # 3. Positive Signal Card
    print("\n3️⃣ POSITIVE SIGNAL CARD")
    positive_card = generate_positive_signal_card()
    post_to_gchat(positive_card, "Positive Signal Card")
    time.sleep(3)
    
    # 4. Weekly Product Digest
    print("\n4️⃣ WEEKLY PRODUCT DIGEST")
    weekly_card = generate_sample_weekly_digest()
    post_to_gchat(weekly_card, "Weekly Product Digest")
    time.sleep(2)
    
    # Post summary message
    summary_msg = {
        "text": "✅ *Sample cards demonstration complete*\n\nThese are the exact formats that will be posted during:\n• Daily signal processing (Client Meeting + Critical/Positive alerts)\n• Weekly digest runs (Product Digest with gap summaries)"
    }
    post_to_gchat(summary_msg, "Summary message")
    
    print("\n" + "=" * 60)
    print("✅ All sample cards posted to Google Chat!")
    print("   Check your Google Chat space to see the formatted cards")
    print("=" * 60)

if __name__ == "__main__":
    main()