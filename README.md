# LeadQualify Content Agent

An autonomous content operations pipeline built for **LeadQualify** (a B2B
lead-scoring SaaS). It researches the competitive landscape, writes on-brand
content, publishes it across platforms, monitors engagement, and qualifies and
replies to interested leads — with a human only reviewing a daily summary.

> Built solo, alongside the core LeadQualify product, to solve a simple problem:
> consistent daily content needs research + writing + scheduling + posting + reply
> management, and there wasn't time to do all of that by hand.

📄 **See [WORKFLOW.md](./WORKFLOW.md) for the full pipeline diagrams and stage-by-stage breakdown.**

![Content pipeline flow](./diagrams/content-pipeline-flow.svg)

## What It Does

- Analyzes competitor content (Apollo, Clay, Warmly) to find what's resonating in the niche
- Generates fresh, on-brand posts with Gemini, enforcing platform-specific formatting via structured JSON output
- Builds and maintains a rolling content calendar
- Publishes automatically to **Instagram** and **LinkedIn** (Meta Graph API / LinkedIn API) and to a **blog**
- Sources topic-matched images from a free stock photo API
- Monitors Instagram comments in real time and scores them for lead intent
- Sends AI-generated replies to qualified leads automatically
- Reports a daily summary via Telegram

## How It Works

Orchestrated with **n8n** (self-hosted via Docker), which triggers Python scripts
through a small Flask bridge service running on the host — needed because Docker
isolates the container from the host filesystem.

Full diagram and stage-by-stage detail: **[WORKFLOW.md](./WORKFLOW.md)**

## Tech Stack

| Layer | Tooling |
|---|---|
| Orchestration | n8n (self-hosted, Docker) |
| LLM | Google Gemini |
| Publishing | Meta Graph API (Instagram), LinkedIn API, dev.to API (blog) |
| Images | Pexels (free stock photo API) |
| Host bridge | Flask |
| Reporting | Telegram Bot API |
| Persistence | Docker restart policies, Windows Task Scheduler |

## Status

Running in production for LeadQualify's own marketing — fully autonomous, scheduled,
no manual intervention beyond the daily Telegram summary.

## Challenges Solved

- Worked through Meta's layered permission system (App Roles → Business Portfolio
  verification → Instagram Tester invitations) to get live posting access
- Adapted to platform API cost changes mid-project (Hashnode's API going paid-only,
  Google image generation having no free tier) by swapping in dev.to and Pexels
- Solved Docker's host-isolation problem with a lightweight internal API bridge
  instead of fighting the container's security model
- Fixed Windows console encoding crashes, LinkedIn OAuth token/permission
  mismatches, and silent failures in scheduled background jobs
