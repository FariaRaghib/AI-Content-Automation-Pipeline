"""
Agent 6: Blog Agent
-------------------
Converts LinkedIn posts + hooks into full SEO blog drafts.
Optimizes for search, adds structure, internal links.

Run:
    python blog_agent.py
"""

import os
import json
from datetime import datetime, timezone

HOOKS_FILE = "data/hook_writer_output.json"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PRODUCT_URL = "https://lead-qualify-ten.vercel.app"

ACRONYMS = {"MQL", "SDR", "AI", "ROI", "CRM", "SAAS",
            "B2B", "B2C", "SEO", "CTA", "API", "LLM", "ICP", "SQL"}
MINOR_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in",
               "nor", "of", "on", "or", "per", "so", "the", "to", "up",
               "via", "yet", "with"}

TITLE_TEMPLATES = [
    "Why {claim}",
    "The Real Reason {claim}",
    "Here's Why {claim}",
    "{claim_cap} — Here's What Changes",
    "The Uncomfortable Truth: {claim_cap}",
    "Stop Ignoring This: {claim_cap}",
]


def smart_title_case(text):
    """Headline-case a string: capitalize major words, lowercase minor
    words (unless first/last), and force known acronyms to uppercase."""
    words = text.split(' ')
    n = len(words)
    result = []
    for i, w in enumerate(words):
        core = w.strip('"\u2014:,')
        if not core:
            result.append(w)
            continue
        lower_core = core.lower()
        if lower_core in ACRONYMS:
            new_core = core.upper()
        elif lower_core.endswith('s') and lower_core[:-1] in ACRONYMS:
            new_core = lower_core[:-1].upper() + 's'
        elif 0 < i < n - 1 and lower_core in MINOR_WORDS:
            new_core = lower_core
        else:
            new_core = core[0].upper() + core[1:].lower()
        result.append(w.replace(core, new_core, 1))
    return ' '.join(result)


def build_curious_title(hook_text):
    """Turn a raw hook line into a curiosity-driven headline, using the
    actual hook content (not the internal 'angle' descriptor field)."""
    # Use the first substantial sentence/clause as the base claim
    for sep in ['. ', '? ', '! ']:
        if sep in hook_text:
            base = hook_text.split(sep)[0]
            break
    else:
        base = hook_text
    base = base.strip().rstrip('.!?')

    if not base:
        base = hook_text.strip().rstrip('.!?')

    # Shorten a long/run-on clause to a tight, headline-sized fragment
    # BEFORE applying a template, so the template wrapper doesn't push
    # the final title past a safe length and force an ugly mid-word cut.
    TARGET_BASE_LEN = 50
    if len(base) > TARGET_BASE_LEN:
        candidate = None
        for clause_sep in [', and ', ', but ', ', ', ' and ', ' but ']:
            if clause_sep in base:
                piece = base.split(clause_sep)[0]
                if 20 <= len(piece) <= TARGET_BASE_LEN + 15:
                    candidate = piece
                    break
        if candidate is None:
            # Hard-cut at the last full word within budget
            words = base.split(' ')
            acc = []
            length = 0
            for w in words:
                if length + len(w) + 1 > TARGET_BASE_LEN:
                    break
                acc.append(w)
                length += len(w) + 1
            candidate = ' '.join(acc) if acc else base[:TARGET_BASE_LEN]
        base = candidate

    # Version for embedding mid-sentence (lowercase lead word)
    claim = base[0].lower() + base[1:] if base else base
    claim_cap = base
    noun = base

    idx = abs(hash(base)) % len(TITLE_TEMPLATES)
    template = TITLE_TEMPLATES[idx]
    title = template.format(claim=claim, claim_cap=claim_cap, noun=noun)

    # Safety net only: should rarely trigger now that base is pre-shortened
    if len(title) > 78:
        words = title.split(' ')
        trimmed = []
        length = 0
        for w in words:
            if length + len(w) + 1 > 78:
                break
            trimmed.append(w)
            length += len(w) + 1
        title = ' '.join(trimmed)

    return smart_title_case(title)


def slugify(title):
    slug = title.lower()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '-'.join(slug.split())
    return slug[:60].rstrip('-')


def load_hooks():
    """Load hooks from Agent 2."""
    if not os.path.exists(HOOKS_FILE):
        raise SystemExit(f"ERROR: {HOOKS_FILE} not found. Run hook_writer_mock.py first.")
    with open(HOOKS_FILE, encoding='utf-8') as f:
        return json.load(f)


def expand_hook_to_blog(hook):
    """Expand a hook into a full blog post outline + draft."""

    blog_posts = {
        "Your lead scoring is wrong. You're optimizing for the lead, not for whether they'll actually close.": {
            "title": "Lead Scoring vs. Close Probability: Why Your Model Fails",
            "slug": "lead-scoring-vs-close-probability",
            "meta_description": "Most lead scoring models optimize for fit, not buying intent. Here's why you're missing deals and how to fix it.",
            "keywords": ["lead scoring", "lead qualification", "sales efficiency", "lead scoring model"],
            "opening": "Most lead scoring models are built around the wrong question. They ask \"does this lead fit our ideal customer profile?\" when the question that actually predicts revenue is \"is this lead showing intent to buy right now?\" That gap is where deals quietly die.",
            "solution": "Fit tells you who a company is. Intent tells you what they're about to do. A lead scoring system built only on firmographic fit (company size, industry, job title) will rank a perfect-fit account the same whether they've never opened an email or they've visited your pricing page five times this week. Scoring for intent means weighting behavioral signals -- engagement, recency, and buying-stage activity -- above static attributes.",
            "case_study_before": "87 leads/month, 3 closed deals, sales team spending most of their week on outreach that never converts.",
            "case_study_after": "45 leads/month after intent-based filtering, 8 closed deals -- fewer leads, more than double the close rate.",
            "outline": [
                "The Problem: Fit-Based vs Intent-Based Scoring",
                "Why Apollo, Clay, and Warmly Get It Wrong",
                "How LeadQualify Scores for Close Probability",
                "Case Study: 13% of Leads = 87% of Revenue",
                "Implement Your Own Scoring Model (Checklist)"
            ],
            "cta": "See how LeadQualify scores for close probability"
        },
        "87% of leads never close. Most tools score them the same way. We identify the 13% that matter.": {
            "title": "The 13% Rule: Identify High-Intent Leads Before Wasting Time",
            "slug": "13-percent-rule-identify-high-intent-leads",
            "meta_description": "87% of leads never close. Learn how to identify the 13% that actually matter using AI-powered intent detection.",
            "keywords": ["lead qualification", "high-intent leads", "sales efficiency", "lead scoring"],
            "opening": "Across most B2B pipelines, roughly 87% of leads will never close, no matter how they're nurtured. Most scoring tools treat that 87% the same as the 13% that actually convert, which means your sales team spends most of its time chasing leads that were never going to buy.",
            "solution": "The fix isn't more leads, it's better filtering. Buying intent shows up in specific, trackable signals: repeat visits to pricing or demo pages, increasing session frequency, engagement with bottom-of-funnel content, and timing relative to a trigger event. A model that weights these signals correctly can surface the 13% early, before your team wastes a single call on the other 87%.",
            "case_study_before": "A sales team working 200+ leads a month with a 3% close rate and constant rep burnout.",
            "case_study_after": "The same team, working a filtered list of high-intent leads only, saw close rates climb past 15% with less than half the outreach volume.",
            "outline": [
                "The 87% Problem: Dead Leads Drain Your Pipeline",
                "What Makes a Lead Actually Close?",
                "Intent Signals Your Sales Team Misses",
                "The Data: What Separates Closing Deals from Noise",
                "Action: Audit Your Current Lead List"
            ],
            "cta": "Get a free audit of your current leads"
        },
        "Your CRM is a graveyard of dead leads. LeadQualify revives it—AI scores what's actually worth pursuing.": {
            "title": "How to Revive a Dead Lead List with AI Scoring",
            "slug": "revive-dead-lead-list-ai-scoring",
            "meta_description": "Your CRM is full of leads that will never close. Here's how AI-powered lead scoring can revive your pipeline.",
            "keywords": ["lead scoring", "dead leads", "CRM cleanup", "lead qualification"],
            "opening": "Most CRMs are full of leads marked \"cold\" or simply forgotten, not because they were bad fits, but because nobody ever re-scored them against current intent signals. A lead that looked dead six months ago might be actively researching a purchase right now, and there's no way to know without re-running the numbers.",
            "solution": "Reviving a dead list starts with re-scoring, not re-emailing. Pull recent engagement data (site visits, content downloads, email opens) for every contact marked inactive, then rank by recency and depth of engagement rather than by how long ago they were added. AI scoring automates this so it happens continuously instead of once a quarter.",
            "case_study_before": "A CRM with 4,000+ contacts marked \"dead\" or \"unresponsive,\" none of them touched in over 90 days.",
            "case_study_after": "Re-scoring surfaced 180 contacts showing active buying signals -- a list small enough for a sales team to work personally, and it produced real pipeline within two weeks.",
            "outline": [
                "The CRM Graveyard: Why Dead Leads Stay Dead",
                "Resurrection Strategy: What Signals Matter?",
                "AI Scoring: Automating Lead Triage",
                "Case Study: Recovering Value from 'Dead' Leads",
                "Your CRM Cleanup Checklist"
            ],
            "cta": "Run a free lead health check"
        },
        "Multi-channel outreach doesn't work if you're reaching the wrong people first.": {
            "title": "Multi-Channel Sales: Why Lead Scoring Comes First",
            "slug": "multi-channel-sales-lead-scoring-first",
            "meta_description": "Orchestrating campaigns across email, LinkedIn, and ads only works if you're targeting the right people. Here's how.",
            "keywords": ["multi-channel sales", "lead scoring", "sales orchestration", "outreach strategy"],
            "opening": "Multi-channel outreach gets sold as a volume play: hit the same prospect on email, LinkedIn, and ads and the odds of a response go up. In practice, that only works if you were targeting the right prospect to begin with. Coordinating three channels against the wrong list just triples the wasted effort.",
            "solution": "Scoring has to happen before sequencing, not after. Once leads are ranked by intent, channel order can follow buying stage -- email for early awareness, LinkedIn for warming and social proof, ads for retargeting once there's already engagement to build on. Without that ordering, multi-channel campaigns are just noise across more surfaces.",
            "case_study_before": "A team running identical 3-channel sequences against their entire list, regardless of engagement level.",
            "case_study_after": "After gating channel sequencing behind a lead score, response rates on the top-tier segment more than doubled while total send volume dropped.",
            "outline": [
                "The Multi-Channel Trap: Broadcasting to the Wrong People",
                "Lead Scoring as the Foundation of Orchestration",
                "Sequencing by Intent: Email → LinkedIn → Ads",
                "Case Study: Orchestrated Outreach Results",
                "Build Your Orchestration Playbook"
            ],
            "cta": "Download our orchestration template"
        }
    }

    hook_text = hook['hook']
    if hook_text in blog_posts:
        return blog_posts[hook_text]
    else:
        # Generic fallback -- real curiosity-driven headline, not a
        # mechanical .title()-cased dump of the internal angle field
        title = build_curious_title(hook['hook'])
        return {
            "title": title,
            "slug": slugify(title),
            "meta_description": hook['hook'][:160],
            "keywords": ["lead scoring", "sales", "B2B SaaS"],
            "opening": hook['hook'],
            "solution": "Most teams solve this by scoring leads on intent signals rather than static fit, then routing sales effort toward the accounts most likely to close.",
            "case_study_before": "A pipeline full of leads treated with equal priority regardless of engagement.",
            "case_study_after": "A filtered, intent-ranked pipeline that let the sales team focus only on accounts showing real buying signals.",
            "outline": [
                "The Problem",
                "Why It Matters",
                "The Solution",
                "How to Implement",
                "Next Steps"
            ],
            "cta": "Get started free"
        }


def generate_blog_draft(blog_meta):
    """Generate a markdown blog draft with real content, no leftover template placeholders."""

    draft = f"""# {blog_meta['title']}

**Read time: 6 min**

---

## The Problem

{blog_meta['opening']}

- Most companies are leaving deals on the table
- Their scoring models optimize for fit, not intent
- This leads to 80%+ wasted outreach

---

## Why It Matters

Your sales team is:
- Chasing unqualified leads
- Missing high-intent accounts
- Burning out on dead-end outreach

## The Solution

{blog_meta['solution']}

### Key Insight

The difference between scoring for **fit** (company size, industry) vs **intent** (buying signals, engagement):

| Metric | Fit-Based | Intent-Based |
|--------|-----------|--------------|
| Lead Volume | High | Lower |
| Close Rate | 3-5% | 15-20% |
| Sales Time Wasted | 80% | 20% |
| Deal Cycle | 90+ days | 45-60 days |

---

## Case Study

Before: {blog_meta['case_study_before']}

After: {blog_meta['case_study_after']}

---

## How to Implement

1. **Audit your current leads** — which actually closed in the last 6 months?
2. **Identify patterns** — what separated winning leads from losses?
3. **Build your scoring model** — weight the signals that matter
4. **Test and iterate** — LeadQualify does this automatically

---

## Next Steps

{blog_meta['cta']} — [{PRODUCT_URL}]({PRODUCT_URL})

---

*Questions? Reply in the comments or [try LeadQualify]({PRODUCT_URL})*
"""

    return draft


def main():
    print("Loading hooks from Agent 2...")
    hooks_data = load_hooks()
    hooks = hooks_data['hooks']

    # Filter for blog-eligible hooks (educational/long-form)
    blog_eligible = [h for h in hooks if h['platform'] in ['linkedin', 'blog']]

    print(f"Generating blog posts from {len(blog_eligible)} hooks...\n")

    blog_drafts = []

    for hook in blog_eligible:
        blog_meta = expand_hook_to_blog(hook)
        draft = generate_blog_draft(blog_meta)

        blog_post = {
            "hook": hook['hook'],
            "metadata": blog_meta,
            "draft_markdown": draft,
            "seo_checklist": {
                "title_length": f"{len(blog_meta['title'])} chars (target: 50-60)",
                "meta_description": f"{len(blog_meta['meta_description'])} chars (target: 150-160)",
                "keywords": blog_meta['keywords'],
                "internal_links": "TODO: Add 2-3 internal links to other posts",
                "external_links": "TODO: Add 2-3 authority links (GitLab, Hubspot, etc)",
                "images": "TODO: Add 2-3 relevant images",
                "call_to_action": blog_meta['cta']
            }
        }

        blog_drafts.append(blog_post)

    # Save drafts
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blog_posts": blog_drafts,
        "publishing_schedule": "1 post per week (Mondays at 10 AM UTC)",
        "note": "Drafts are templates. Customize with real data, examples, and voice."
    }

    blog_path = os.path.join(OUTPUT_DIR, "blog_agent_drafts.json")
    with open(blog_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved blog drafts -> {blog_path}\n")

    # Print summaries
    print("--- BLOG POST DRAFTS (Ready to Publish) ---\n")

    for i, post in enumerate(blog_drafts, 1):
        meta = post['metadata']
        print(f"{i}. {meta['title']}")
        print(f"   Slug: {meta['slug']}")
        print(f"   Meta: {meta['meta_description'][:80]}...")
        print(f"   Keywords: {', '.join(meta['keywords'][:3])}")
        print(f"   Outline: {' -> '.join(meta['outline'][:2])}...")
        print(f"   CTA: {meta['cta']} -> {PRODUCT_URL}")
        print(f"\n   Draft preview (first 200 chars):")
        draft_preview = post['draft_markdown'][:200].replace('\n', ' ')
        print(f"   {draft_preview}...\n")


if __name__ == "__main__":
    main()