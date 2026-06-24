#!/usr/bin/env python3
"""
Sample Daily Digest Output - Shows what would be posted to GChat
"""

import json
from datetime import datetime

def generate_sample_client_meeting_card():
    """Generate a sample client meeting card with signals"""
    
    card = {
        "cardsV2": [{
            "cardId": "pinnacle-properties-2026-06-24",
            "card": {
                "header": {
                    "title": "⚠️ Client Meeting · Pinnacle Properties",
                    "subtitle": "2026-06-24 · Hyly lead: Sarah Johnson"
                },
                "sections": [
                    {
                        "header": "Business Signals",
                        "widgets": [
                            {"textParagraph": {"text": "<b>1. 🔴 ACT NOW · Product gap</b>"}},
                            {"textParagraph": {"text": "<b>Renewal automation desperately needed</b>"}},
                            {"textParagraph": {"text": "<font color=\"#888888\">Why it matters</font>\nClient spending 3+ hours weekly on manual renewal processing. Risk of churn if not addressed. \"We're drowning in manual renewals - our team spends entire mornings just processing them.\""}}
                        ]
                    },
                    {
                        "widgets": [
                            {"textParagraph": {"text": "<b>2. 🟡 WATCH · Expectation gap</b>"}},
                            {"textParagraph": {"text": "<b>Expected bulk edit for resident data</b>"}},
                            {"textParagraph": {"text": "<font color=\"#888888\">Why it matters</font>\nAssumed feature parity with competitors. May impact adoption across portfolio. \"I thought for sure you'd have bulk editing - every other platform does.\""}}
                        ]
                    },
                    {
                        "widgets": [
                            {"textParagraph": {"text": "<b>3. 🟢 HEALTHY · Positive signal</b>"}},
                            {"textParagraph": {"text": "<b>Strong endorsement of Hayley's accuracy</b>"}},
                            {"textParagraph": {"text": "<font color=\"#888888\">Why it matters</font>\nPotential case study opportunity. Client seeing 95% accuracy in lead qualification. \"Hayley has been incredibly accurate - we trust it completely now.\""}}
                        ]
                    },
                    {
                        "header": "Links",
                        "widgets": [
                            {"buttonList": {"buttons": [
                                {"text": "OPEN IN NOTION", "onClick": {"openLink": {"url": "https://notion.so/pinnacle-2026-06-24"}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def generate_critical_gap_alert():
    """Generate a critical gap alert card"""
    
    card = {
        "cardsV2": [{
            "cardId": "critical-gap-gap-product-renewal-automation",
            "card": {
                "header": {
                    "title": "🚨 Critical Gap Alert",
                    "subtitle": "Pinnacle Properties — 2026-06-24 — Sarah Johnson"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "decoratedText": {
                                    "topLabel": "Signal",
                                    "text": "<b>gap-product-renewal-automation</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "MRR",
                                    "text": "<b>$45,000/month</b>"
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
                                    "text": "<i>\"We're drowning in manual renewals - our team spends entire mornings just processing them. If we can't automate this by Q2, we'll have to look at alternatives.\"</i>"
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
                                {"text": "VIEW IN NOTION", "onClick": {"openLink": {"url": "https://notion.so/pinnacle-2026-06-24"}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def generate_positive_signal_card():
    """Generate a positive signal card"""
    
    card = {
        "cardsV2": [{
            "cardId": "positive-20260624-greystar",
            "card": {
                "header": {
                    "title": "🟢 Positive Signal",
                    "subtitle": "Greystar — 2026-06-24 — Michael Chen"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "decoratedText": {
                                    "topLabel": "Subtype",
                                    "text": "<b>expansion_intent</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "MRR",
                                    "text": "<b>$125,000/month</b>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": "<i>\"We're so happy with the results at our California portfolio that we're ready to roll out to Texas and Florida - probably another 50 properties by year end.\"</i>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "topLabel": "Suggested Action",
                                    "text": "Alert CSM + AE for follow-up"
                                }
                            }
                        ]
                    },
                    {
                        "widgets": [
                            {"buttonList": {"buttons": [
                                {"text": "VIEW IN NOTION", "onClick": {"openLink": {"url": "https://notion.so/greystar-2026-06-24"}}}
                            ]}}
                        ]
                    }
                ]
            }
        }]
    }
    
    return card

def generate_sample_weekly_digest():
    """Generate a sample weekly product digest"""
    
    card = {
        "cardsV2": [{
            "cardId": "weekly-digest-20260624",
            "card": {
                "header": {
                    "title": "📊 Weekly Product Digest",
                    "subtitle": "Jun 17 - Jun 24, 2026",
                    "imageUrl": "https://fonts.gstatic.com/s/i/googlematerialicons/insights/v6/24px.svg",
                    "imageType": "CIRCLE"
                },
                "sections": [
                    {
                        "header": "Summary",
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>15 product signals this week</b>"
                                }
                            },
                            {
                                "decoratedText": {
                                    "startIcon": {
                                        "knownIcon": "BOOKMARK"
                                    },
                                    "text": "🔴 3 Critical - Immediate PM attention required"
                                }
                            },
                            {
                                "decoratedText": {
                                    "startIcon": {
                                        "knownIcon": "CLOCK"
                                    },
                                    "text": "🟡 7 High - Address this sprint"
                                }
                            }
                        ]
                    },
                    {
                        "header": "🔴 CRITICAL GAPS",
                        "collapsible": False,
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>🔴 gap-product-renewal-automation</b>\n" +
                                            "Multiple enterprise clients need automated renewal processing to reduce 3+ hours of manual work weekly.\n" +
                                            "Clients: 4 | Status: theme\n" +
                                            "<i>\"We're drowning in manual renewals - our team spends entire mornings just processing them.\"</i>\n" +
                                            "<a href=\"https://notion.so/pinnacle-renewal\">View in Notion</a>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": "<b>🔴 gap-product-bulk-resident-updates</b>\n" +
                                            "Large portfolios unable to efficiently update resident data across multiple properties at once.\n" +
                                            "Clients: 3 | Status: emerging\n" +
                                            "<i>\"Updating 500+ residents one by one is killing our productivity.\"</i>\n" +
                                            "<a href=\"https://notion.so/greystar-bulk\">View in Notion</a>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": "<b>🔴 limit-integration-salesforce-sync</b>\n" +
                                            "Enterprise clients blocked from Salesforce integration causing duplicate data entry and delays.\n" +
                                            "Clients: 2 | Status: emerging\n" +
                                            "<i>\"Without Salesforce sync, we're maintaining two systems manually.\"</i>\n" +
                                            "<a href=\"https://notion.so/equity-salesforce\">View in Notion</a>"
                                }
                            }
                        ]
                    },
                    {
                        "header": "🟡 HIGH PRIORITY",
                        "collapsible": True,
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>🟡 expectation-workflow-approval-chains</b>\n" +
                                            "Users expected multi-level approval workflows similar to competitor platforms.\n" +
                                            "Clients: 2 | Status: candidate\n" +
                                            "<a href=\"https://notion.so/lincoln-approvals\">View in Notion</a>"
                                }
                            },
                            {
                                "textParagraph": {
                                    "text": "<b>🟡 gap-reporting-custom-dashboards</b>\n" +
                                            "Portfolio managers need customizable dashboards for executive reporting.\n" +
                                            "Clients: 2 | Status: candidate\n" +
                                            "<a href=\"https://notion.so/camden-dashboards\">View in Notion</a>"
                                }
                            }
                        ]
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

def main():
    print("=" * 60)
    print("SAMPLE DAILY DIGEST OUTPUT")
    print("Date: " + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print("=" * 60)
    
    print("\n1️⃣ CLIENT MEETING CARD (Main signals from call)")
    print("-" * 40)
    meeting_card = generate_sample_client_meeting_card()
    print(json.dumps(meeting_card, indent=2))
    
    print("\n" + "=" * 60)
    print("\n2️⃣ CRITICAL GAP ALERT (For high-severity product gaps)")
    print("-" * 40)
    critical_card = generate_critical_gap_alert()
    print(json.dumps(critical_card, indent=2))
    
    print("\n" + "=" * 60)
    print("\n3️⃣ POSITIVE SIGNAL CARD (For growth opportunities)")
    print("-" * 40)
    positive_card = generate_positive_signal_card()
    print(json.dumps(positive_card, indent=2))
    
    print("\n" + "=" * 60)
    print("\n4️⃣ WEEKLY PRODUCT DIGEST (Aggregated weekly view)")
    print("-" * 40)
    weekly_card = generate_sample_weekly_digest()
    # Show just first part due to length
    print(json.dumps(weekly_card, indent=2)[:2000] + "...\n[Card continues with more signals]")
    
    print("\n" + "=" * 60)
    print("\n✅ These cards would be posted to Google Chat in this exact format")
    print("   Each card type serves a specific purpose:")
    print("   • Client Meeting: All signals from a single call")
    print("   • Critical Gap: Urgent product gaps requiring PM attention")
    print("   • Positive Signal: Growth/expansion opportunities")
    print("   • Weekly Digest: Aggregated view with gap summaries")

if __name__ == "__main__":
    main()