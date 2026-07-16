# Workflow

This document details how the LeadQualify Content Agent pipeline runs end to end,
from competitor research to lead engagement.

## Pipeline Diagram

**Part 1 — Content creation and publishing**

![Content pipeline flow: scheduled trigger, competitor research, content generation, content calendar and image sourcing, then publishing to Instagram, LinkedIn, and blog](./diagrams/content-pipeline-flow.svg)

**Part 2 — Engagement and reporting**

![Engagement and reporting flow: new Instagram comment, lead scoring, qualified lead decision branching to AI reply or log and skip, converging into daily summary and Telegram report](./diagrams/engagement-reporting-flow.svg)

<details>
<summary>Mermaid source (single-diagram view)</summary>

```mermaid
flowchart TD
    A[Scheduled Trigger<br/>n8n cron] --> B[Competitor Research<br/>Apollo, Clay, Warmly]
    B --> C[Content Generation<br/>Gemini LLM → structured JSON]
    C --> D[Content Calendar<br/>rolling schedule]
    D --> E[Image Sourcing<br/>free stock photo API]
    E --> F{Publish}
    F --> F1[Instagram<br/>Meta Graph API]
    F --> F2[LinkedIn API]
    F --> F3[Blog<br/>dev.to]

    F1 --> G[Comment Monitoring<br/>real-time polling]
    G --> H[Lead Scoring<br/>intent-signal analysis]
    H --> I{Qualified Lead?}
    I -- Yes --> J[AI-Generated Reply]
    I -- No --> K[Log & Skip]

    F1 & F2 & F3 --> L[Daily Summary]
    J --> L
    L --> M[Telegram Report]

    subgraph Infra["Reliability Layer"]
        N[Flask Bridge Service<br/>host ↔ Docker container]
        O[Docker Restart Policy]
        P[Windows Task Scheduler]
        Q[Retry Logic + Fallbacks]
    end

    A -.orchestrated via.-> N
    N -.always-on.-> O
    N -.survives reboot.-> P
    C -.wrapped with.-> Q
    F1 -.wrapped with.-> Q
```

</details>

## Stage-by-Stage Breakdown

### 1. Trigger
n8n (self-hosted in Docker) fires the pipeline on a schedule. Because Docker isolates
the container's filesystem from the host, n8n calls a lightweight **Flask bridge
service** running on the host machine, which is what actually executes the Python
scripts.

### 2. Research
The agent pulls recent content from competitor accounts (Apollo, Clay, Warmly) to
identify what formats and topics are currently performing well in the niche.

### 3. Generate
Research findings are passed to Gemini with a prompt enforcing:
- On-brand voice and tone
- Platform-specific length/format constraints (Instagram vs. LinkedIn vs. blog)
- Structured JSON output, so downstream steps never have to parse free-form text

### 4. Schedule
Generated posts are slotted into a rolling content calendar rather than posted
immediately, so cadence stays consistent even if a generation run produces more or
less content than usual.

### 5. Source Images
Each post is matched with a topically relevant image pulled from a free stock photo
API (Pexels) — a fallback adopted after confirming neither Meta's nor Google's
image-generation options were free at the volume needed.

### 6. Publish
Posts go out automatically via:
- **Meta Graph API** → Instagram
- **LinkedIn API** → LinkedIn
- **dev.to API** → Blog (after Hashnode moved its API behind a paywall mid-project)

### 7. Monitor Engagement
A polling job watches new Instagram comments in near real time.

### 8. Score & Respond
Each comment is scored for buying intent using a lead-scoring algorithm. Comments
that clear the qualification threshold get an AI-generated reply; the rest are
logged and skipped.

### 9. Report
A daily summary — posts published, engagement, leads qualified — is sent via
Telegram, which is the only manual touchpoint in the system.

## Reliability Design

| Concern | Solution |
|---|---|
| Container can't reach host scripts | Flask bridge service exposes an internal API |
| Machine reboots | Docker restart policies (n8n) + Windows Task Scheduler (bridge service) |
| Flaky network calls | Retry logic on all external API calls |
| Partial failures | Fallback logic so the pipeline degrades gracefully instead of failing silently |
| Windows console crashes | Fixed console encoding issues in the bridge service |
| LinkedIn OAuth mismatches | Corrected token/permission scope configuration |

## Permissions & Access Notes

Getting live posting access required working through Meta's layered permission
system: App Roles → Business Portfolio verification → Instagram Tester invitations.
Budget time for this when replicating the pipeline — it's typically the slowest step.
