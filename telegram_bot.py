"""
Telegram Bot: Daily Digest
---------------------------
Sends you a daily report of:
- Posts scheduled for today
- Qualified leads from comments
- Performance metrics
- Recommendations

Set up: Create a scheduled task (cron job) to run this daily at 8 AM

Run:
    python telegram_bot.py

Or on schedule:
    # Linux/Mac: Add to crontab
    0 8 * * * cd /path/to/leadqualify-agents && python telegram_bot.py
    
    # Windows: Task Scheduler (run daily at 8 AM)
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import urllib.request
import urllib.parse

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
    posts_text = "📅 **Today's Posts**\n"
    if todays_posts:
        for post in todays_posts:
            posts_text += f"\n⏰ {post['time']} UTC on {post['platform'].upper()}\n"
            posts_text += f"_\"{post['hook'][:80]}...\"_\n"
    else:
        posts_text += "No posts scheduled today.\n"
    
    # Top leads
    leads = data.get('leads', {})
    top_leads = get_top_leads(leads)
    leads_text = "\n🎯 **New Qualified Leads**\n"
    if top_leads:
        leads_text += f"Found {len(leads.get('qualified_leads', []))} qualified leads from comments.\n\n"
        for lead in top_leads:
            leads_text += f"• {lead['commenter_name']} ({lead['commenter_title']})\n"
            leads_text += f"  Score: {lead['lead_score']}/100\n"
    else:
        leads_text += "No new leads yet.\n"
    
    # Analytics
    analyst = data.get('analyst', {})
    stats = analyst.get('platform_stats', {})
    analytics_text = "\n📊 **Performance**\n"
    if stats:
        if 'linkedin' in stats:
            analytics_text += f"LinkedIn: {stats['linkedin']['avg_engagement_rate']*100:.1f}% engagement\n"
        if 'instagram' in stats:
            analytics_text += f"Instagram: {stats['instagram']['avg_engagement_rate']*100:.1f}% engagement\n"
        if 'blog' in stats:
            analytics_text += f"Blog: {stats['blog']['avg_monthly_views']} monthly views\n"
    
    # Recommendations
    recs = get_top_recommendations(analyst)
    recs_text = "\n💡 **Top Recommendations**\n"
    if recs:
        for i, rec in enumerate(recs, 1):
            recs_text += f"\n{i}. {rec['recommendation']}\n"
    
    # Compile full message
    full_message = f"""🤖 **LeadQualify Content Agent — Daily Digest**

{posts_text}{leads_text}{analytics_text}{recs_text}

---
_Report generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_
"""
    
    return full_message


def send_telegram_message(message):
    """Send message to Telegram."""
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(TELEGRAM_API_URL, data=data)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                print("✓ Daily digest sent to Telegram")
                return True
            else:
                print(f"❌ Telegram API error: {result.get('description')}")
                return False
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False


def main():
    print("Loading daily digest data...")
    data = load_data()
    
    if not data:
        print("⚠️  No data files found. Run agents 1-4 first.")
        return
    
    print("Formatting daily digest message...")
    message = format_message(data)
    
    # Print to console
    print("\n" + "="*60)
    print(message)
    print("="*60 + "\n")
    
    # Send to Telegram
    print("Sending to Telegram...")
    success = send_telegram_message(message)
    
    if success:
        print("\n✓ Daily digest complete!")
    else:
        print("\n⚠️  Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")


if __name__ == "__main__":
    main()
