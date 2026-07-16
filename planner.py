"""
Agent 3: Planner
----------------
Reads hooks from Agent 2, builds a weekly content calendar.
Assigns optimal posting times per platform.

Run:
    python planner.py
"""

import os
import json
from datetime import datetime, timedelta, timezone

HOOKS_FILE = "data/hook_writer_output.json"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Platform posting schedule (optimal times for B2B SaaS)
PLATFORM_SCHEDULE = {
    "linkedin": {
        "days": [1, 3, 4],  # Tuesday, Thursday, Friday (0=Monday)
        "time": "09:00",    # 9 AM
        "frequency": "3x/week"
    },
    "instagram": {
        "days": [2, 4],     # Wednesday, Friday
        "time": "19:00",    # 7 PM
        "frequency": "2x/week"
    },
    "blog": {
        "days": [0],        # Monday
        "time": "10:00",    # 10 AM
        "frequency": "1x/week"
    }
}


def load_hooks():
    """Load hooks from Agent 2 output."""
    if not os.path.exists(HOOKS_FILE):
        raise SystemExit(f"ERROR: {HOOKS_FILE} not found. Run hook_writer_mock.py first.")
    with open(HOOKS_FILE, encoding='utf-8') as f:
        return json.load(f)


def build_calendar(hooks_data):
    """Build a 2-week content calendar from hooks."""
    hooks = hooks_data['hooks']
    
    # Start from next Monday
    today = datetime.now(timezone.utc)
    days_ahead = 0 - today.weekday()  # 0 = Monday
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    
    calendar = []
    day_counters = {
        "linkedin": 0,
        "instagram": 0,
        "blog": 0
    }
    
    # Group hooks by platform
    hooks_by_platform = {}
    for hook in hooks:
        platform = hook['platform']
        if platform not in hooks_by_platform:
            hooks_by_platform[platform] = []
        hooks_by_platform[platform].append(hook)

    # Safety net: if the AI didn't generate hooks for a platform we need
    # (e.g. all 5 came back as "linkedin"), borrow from the full pool instead
    # of leaving that platform empty in the calendar.
    for platform in PLATFORM_SCHEDULE:
        if platform not in hooks_by_platform or not hooks_by_platform[platform]:
            hooks_by_platform[platform] = hooks  # fall back to all hooks
    
    # Generate 14-day calendar
    for week in range(2):
        for day_of_week in range(7):
            current_date = next_monday + timedelta(days=day_of_week + (week * 7))
            
            # Check each platform's schedule for this day
            for platform, schedule in PLATFORM_SCHEDULE.items():
                if day_of_week in schedule['days']:
                    if platform in hooks_by_platform:
                        hook_list = hooks_by_platform[platform]
                        hook_idx = day_counters[platform] % len(hook_list)
                        hook = hook_list[hook_idx]
                        day_counters[platform] += 1
                        
                        calendar.append({
                            "date": current_date.strftime("%Y-%m-%d"),
                            "day": current_date.strftime("%A"),
                            "platform": platform,
                            "time": schedule['time'],
                            "hook": hook['hook'],
                            "angle": hook['angle'],
                            "cta": hook['cta'],
                            "week": week + 1
                        })
    
    return sorted(calendar, key=lambda x: x['date'])


def main():
    print("Loading hooks from Agent 2...")
    hooks_data = load_hooks()
    
    print("Building 2-week content calendar...")
    calendar = build_calendar(hooks_data)
    
    # Save calendar
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar": calendar,
        "posting_guidelines": {
            "linkedin": "Post 3x/week at 9 AM UTC (adjust for your timezone). Use longer captions, tag relevant accounts.",
            "instagram": "Post 2x/week at 7 PM UTC. Use Stories for CTAs, Reels for reach, Carousel for education.",
            "blog": "Publish 1x/week on Mondays. Optimize for SEO, repurpose from video/LinkedIn content."
        }
    }
    
    calendar_path = os.path.join(OUTPUT_DIR, "planner_calendar.json")
    with open(calendar_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved calendar -> {calendar_path}\n")
    
    # Print readable calendar
    print("--- 2-WEEK CONTENT CALENDAR ---\n")
    current_week = 0
    for post in calendar:
        if post['week'] != current_week:
            current_week = post['week']
            print(f"\n[DATE] WEEK {current_week}\n")
        
        print(f"{post['date']} ({post['day']}) @ {post['time']} UTC")
        print(f"Platform: {post['platform'].upper()}")
        print(f"Hook: {post['hook']}")
        print(f"Angle: {post['angle']}")
        print(f"CTA: {post['cta']}")
        print()


if __name__ == "__main__":
    main()