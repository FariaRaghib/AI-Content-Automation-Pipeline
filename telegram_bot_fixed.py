"""
Telegram Bot (FIXED VERSION)
----------------------------
Uses requests library instead of urllib for better Windows compatibility.

Install: pip install requests

Run:
    python telegram_bot_fixed.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Try to import requests, fall back to urllib if not available
try:
    import requests
    USE_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    USE_REQUESTS = False
    print("[WARN]  'requests' library not installed.")
    print("   Run: pip install requests")
    print("   Using urllib fallback...\n")

load_dotenv()

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise SystemExit("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Data files
CALENDAR_FILE = "data/planner_calendar.json"
LEADS_FILE = "data/dm_manager_leads.json"
ANALYST_FILE = "data/analyst_output.json"


def load_data():
    """Load all data files."""
    data = {}
    
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, encoding='utf-8') as f:
            data['calendar'] = json.load(f)
    
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, encoding='utf-8') as f:
            data['leads'] = json.load(f)
    
    if os.path.exists(ANALYST_FILE):
        with open(ANALYST_FILE, encoding='utf-8') as f:
            data['analyst'] = json.load(f)
    
    return data


def get_todays_posts(calendar_data):
    """Get posts scheduled for today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    calendar = calendar_data.get('calendar', [])
    todays = [p for p in calendar if p['date'] == today]
    return todays


def get_top_leads(leads_data):
    """Get top 3 qualified leads."""
    qualified = leads_data.get('qualified_leads', [])
    return qualified[:3]


def get_top_recommendations(analyst_data):
    """Get top 2 recommendations."""
    recs = analyst_data.get('recommendations', [])
    return [r for r in recs if r['priority'] == 'high'][:2]


def format_message(data):
    """Format daily digest as a Telegram message."""
    
    # Posts for today
    todays_posts = get_todays_posts(data.get('calendar', {}))
    posts_text = "[DATE] **Today's Posts**\n"
    if todays_posts:
        for post in todays_posts:
            posts_text += f"\n⏰ {post['time']} UTC on {post['platform'].upper()}\n"
            posts_text += f"_\"{post['hook'][:80]}...\"_\n"
    else:
        posts_text += "No posts scheduled today.\n"
    
    # Top leads
    leads = data.get('leads', {})
    top_leads = get_top_leads(leads)
    leads_text = "\n[LEADS] **New Qualified Leads**\n"
    if top_leads:
        leads_text += f"Found {len(leads.get('qualified_leads', []))} qualified leads from comments.\n\n"
        for lead in top_leads:
            name = lead.get('commenter_name', 'Unknown')
            title = lead.get('commenter_title')  # may not exist for real IG comments
            score = lead.get('lead_score', '?')
            if title:
                leads_text += f"• {name} ({title})\n"
            else:
                leads_text += f"• {name}\n"
            leads_text += f"  Score: {score}/100\n"
    else:
        leads_text += "No new leads yet.\n"
    
    # Analytics - handles BOTH mock schema (avg_engagement_rate directly)
    # and the real/live schema (raw_posts list, notes, etc.) without crashing.
    analyst = data.get('analyst', {})
    stats = analyst.get('platform_stats', {})
    analytics_text = "\n[STATS] **Performance**\n"

    if stats:
        # LinkedIn
        li = stats.get('linkedin', {})
        if 'avg_engagement_rate' in li:
            analytics_text += f"LinkedIn: {li['avg_engagement_rate']*100:.1f}% engagement (mocked)\n"
        elif li:
            analytics_text += f"LinkedIn: {li.get('note', 'no data yet')}\n"

        # Instagram
        ig = stats.get('instagram', {})
        if 'avg_engagement_rate' in ig:
            analytics_text += f"Instagram: {ig['avg_engagement_rate']*100:.1f}% engagement\n"
        elif 'raw_posts' in ig:
            post_count = len(ig['raw_posts'])
            analytics_text += f"Instagram: {post_count} post(s) tracked — {ig.get('note', '')}\n"
        elif ig:
            analytics_text += f"Instagram: {ig.get('note', 'no data yet')}\n"

        # Blog
        blog = stats.get('blog', {})
        if 'avg_monthly_views' in blog:
            analytics_text += f"Blog: {blog['avg_monthly_views']} monthly views (mocked)\n"
        elif 'total_articles' in blog:
            analytics_text += f"Blog: {blog['total_articles']} article(s), {blog.get('avg_views_per_article', 0)} avg views\n"
        elif blog:
            analytics_text += f"Blog: {blog.get('note', 'no data yet')}\n"
    
    # Recommendations
    recs = get_top_recommendations(analyst)
    recs_text = "\n[TIP] **Top Recommendations**\n"
    if recs:
        for i, rec in enumerate(recs, 1):
            recs_text += f"\n{i}. {rec['recommendation']}\n"
    
    # Compile full message
    full_message = f"""[BOT] **LeadQualify Content Agent — Daily Digest**

{posts_text}{leads_text}{analytics_text}{recs_text}

---
_Report generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_
"""
    
    return full_message


def send_telegram_message_requests(message, max_retries=3):
    """Send message using requests library (preferred), with retries."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(TELEGRAM_API_URL, json=payload, timeout=30)
            result = response.json()

            if result.get('ok'):
                print("[OK] Daily digest sent to Telegram")
                return True
            else:
                print(f"[FAIL] Telegram API error: {result.get('description')}")
                return False

        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[WARN] Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                import time
                time.sleep(2)  # brief pause before retry

    print(f"[FAIL] Request failed after {max_retries} attempts: {last_error}")
    return False


def send_telegram_message_urllib(message):
    """Send message using urllib (fallback)."""
    import urllib.request
    import urllib.parse
    import ssl
    
    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(TELEGRAM_API_URL, data=data)
        
        # Use SSL context that works on Windows
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=context, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if result.get('ok'):
            print("[OK] Daily digest sent to Telegram")
            return True
        else:
            print(f"[FAIL] Telegram API error: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Failed to send: {e}")
        print("\nTroubleshooting:")
        print("1. Check your internet connection")
        print("2. Run: python test_telegram_connection.py")
        print("3. Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        print("4. Try: pip install requests")
        return False


def main():
    print("Loading daily digest data...")
    data = load_data()
    
    if not data:
        print("[WARN]  No data files found. Run agents 1-4 first.")
        return
    
    print("Formatting daily digest message...")
    message = format_message(data)
    
    # Print to console
    print("\n" + "="*60)
    print(message)
    print("="*60 + "\n")
    
    # Send to Telegram
    print("Sending to Telegram...")
    
    if USE_REQUESTS:
        success = send_telegram_message_requests(message)
    else:
        success = send_telegram_message_urllib(message)
    
    if success:
        print("\n[OK] Daily digest complete!")
    else:
        print("\n[WARN]  Telegram notification failed, but agents ran successfully!")
        print("   Check n8n dashboard or logs manually")


if __name__ == "__main__":
    main()