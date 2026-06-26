# hyly-signal-intelligence

Signal pipeline for Hyly.AI client calls. Reads transcripts from Notion MeetingDiary, extracts intelligence using Signal Taxonomy v2, applies revenue weighting, routes to 3 GChat feeds, and builds a compounding theme registry in this repo.

**The pipeline engine is a Claude skill** (`skill/km-signal-pipeline.md`), not Python. Claude runs the skill from GitHub Actions; all routing values live in `config/*.json`.

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │  Notion MeetingDiary  (SOURCE — read only)   │
                    │  • Status = Recent Client Meeting            │
                    │  • Meeting Type, Meeting Date, Hyly Lead     │
                    │  • GDrive Transcript URL                     │
                    │  • 📈 DealStrategy relation → MRR            │
                    └───────────────────────┬─────────────────────┘
                                            │ notion-search / notion-fetch
                                            ▼
   config/ (read first) ───────►  ┌───────────────────────────────┐
     call-filter.json             │   km-signal-pipeline           │  ◄─── triggered by
     taxonomy.json                │   (Claude skill, Steps 1–9)    │       .github/workflows/
     mrr-thresholds.json          │                                │         daily-ingest.yml
     gchat-templates.json         │  1 query → 2 MRR → 3 transcript│         weekly-digest.yml
                                  │  4 detect → 5 weight → 6 dedupe│
   Google Drive ──VTT──────────►  │  7 route  → 8 themes → 9 mark  │
                                  └───┬──────────────────┬─────────┘
                                      │                  │
                  Git (signal log)    │                  │   POST card JSON
                ┌─────────────────────▼──────┐           ▼   (built from gchat-templates.json)
                │ themes/[theme_slug].md      │      ┌──────────────────────────────┐
                │   compounding wiki layer    │      │  GChat — 3 feeds              │
                │ digests/YYYY-WW.md          │      │   client_meeting_feed         │
                │   weekly compiled digest    │      │   product_digest_feed         │
                │ feature-requests.md         │      │   marketing_feed              │
                │   feature_gap rollup ledger │      └──────────────────────────────┘
                └─────────────────────────────┘
                                      │
                                      │ one write back only:
                                      ▼
                    Notion: Added to Google Chat = true  (per processed page)
```

**Notion is read-only** except for one write: `Added to Google Chat = true` on each processed MeetingDiary page. `Upcoming` meetings are never processed or posted.

**Git is the signal log.** Theme files are the durable, cross-client intelligence record. Every occurrence links back to its Notion meeting page.

---

## Every file in this repo

| Path | What it is |
|------|-----------|
| `README.md` | This file — architecture, file map, setup, triggering, and the selection/promotion rules. |
| `CLAUDE.md` | Behavioral spec Claude must follow when running in this repo (slug rules, theme-file rules, TEST_MODE, commit format, file policy). |
| `skill/km-signal-pipeline.md` | **The pipeline engine.** Steps 1–9, card formats, severity rubric, error handling. This is what Claude executes. |
| `config/call-filter.json` | Which Notion pages qualify: allowed `Status`, allowed `Meeting Type` list, transcript-URL field priority. |
| `config/taxonomy.json` | The 12 signal types — each with its **definition**, `category`, `owner`, and target `feeds`. Source of truth for routing and type boundaries. |
| `config/mrr-thresholds.json` | `mrr_high_threshold`, the per-feed `severity_scales`, and the `severity_bump_when_mrr_high` promotion rules. |
| `config/gchat-templates.json` | The only source for GChat card JSON (client meeting, critical gap, weekly digest, positive signal). Skill fills placeholders and POSTs. |
| `themes/[theme_slug].md` | One file per named theme. Frontmatter (`status`, `client_count`, `first_seen`, `last_seen`) + an Occurrences table with a Notion link, quote, and timestamp per sighting. Updated every run. |
| `digests/YYYY-WW.md` | Weekly compiled product digest, generated Monday and posted to `product_digest_feed`. |
| `feature-requests.md` | Human-readable running ledger of every `feature_gap` signal — a rollup of the `feature_gap_*` theme files, with title/client/MRR/approval status. Maintained manually. |
| `history.md` | Canonical iteration record. Every behavior-affecting change (skill/config/workflows) adds a dated Change-log entry here. Also documents the removed legacy Python prototypes. |
| `.github/workflows/daily-ingest.yml` | Daily ingest (Mon–Fri 09:00 UTC + manual dispatch with optional `date_range`/`client_filter`). Installs Claude CLI, configures MCP, runs the skill, commits `themes/`+`digests/`. |
| `.github/workflows/weekly-digest.yml` | Monday digest (10:00 UTC + manual). Compiles the past 7 days of product signals into `digests/` and posts the weekly card. |
| `.githooks/pre-commit` | Pre-commit guard: hard-blocks `.py` files and warns if skill/config/workflow changed without a `history.md` update. Enable once per clone (see Setup). |
| `.gitignore` | Blocks `*.py`, `__pycache__/`, `*.pyc` — enforces the no-Python policy. |

---

## Feeds

| Feed | Audience | Cadence | Signal types |
|------|----------|---------|--------------|
| `client_meeting_feed` | Senior leaders | Daily — top 3 signals per call | All 12 types |
| `product_digest_feed` | PM & EA | Critical gaps same-day; weekly digest Monday | feature_gap, expectation, limit |
| `marketing_feed` | Marketing | Per positive signal | positive |

---

## Selection & promotion rules

These are the rules that decide what gets surfaced and how loud. Full logic is in
`skill/km-signal-pipeline.md`; the values are in `config/mrr-thresholds.json`.

**Severity rubric (content only, Step 4).** Each signal is scored on its feed's scale:

| client scale | product scale | Meaning |
|---|---|---|
| `act_now` | `high` | Blocks the client's stated goal now / churn language / deadlined ask. |
| `watch` | `medium` | Real friction but has a workaround or no deadline. |
| `healthy` | `low` | Informational, minor, or positive-leaning. |

**Revenue promotion (Step 5) — the only promotion step.** If the account is high-MRR
(`MRR > mrr_high_threshold`, currently $5,000), severity bumps one rung:
`watch → act_now` on the client feed; `low → medium → high → critical` on the product feed.

**How a Critical Gap is selected.** A product signal (`feature_gap`/`expectation`/`limit`)
reaches `critical` **only** when its content rubric was `high` **and** the account is
high-MRR. Each critical signal posts a 🚨 *Critical Gap Alert* to `product_digest_feed`
immediately, any day. Non-critical product signals wait for the Monday digest.

**How the 3 client-meeting signals are selected.** All detected signals for a call are
ranked by final severity (`act_now` > `watch` > `healthy`), ties broken by MRR tier then
detection order; the top 3 fill the 🔴/🟡/🟢 rows. The card is capped at 3, but **all**
detected signals (up to 6 per call) are still written to `themes/`.

**Theme status promotion.** `candidate` (1 client) → `emerging` (2) → `theme` (3+),
based on `client_count` in the theme file's Occurrences table.

---

## Setup (per clone)

This repo has no install step — the engine is a Claude skill. The only one-time action is
enabling the git hooks:

```bash
git config core.hooksPath .githooks
```

That activates the pre-commit guard (blocks `.py`, reminds you to update `history.md`).
The GitHub Actions runners install everything else at run time (Claude CLI + Notion/GDrive
MCP servers) — see `daily-ingest.yml`. There is no Python and no `requirements.txt`;
`*.py` is intentionally git-ignored and blocked by the hook.

---

## Triggering

### Scheduled
- Daily ingest: Mon–Fri 09:00 UTC (`daily-ingest.yml`)
- Weekly digest: Monday 10:00 UTC, after daily ingest (`weekly-digest.yml`)

### Manual via GitHub UI
Actions → Daily Signal Ingest → Run workflow (optionally set `date_range` / `client_filter`).

### Manual via API
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/debarchana26/hyly-signal-intelligence/actions/workflows/daily-ingest.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "date_range": "2026-06-23",
      "client_filter": "Hines"
    }
  }'
```

`date_range` accepts a single date (`YYYY-MM-DD`) or an inclusive range
(`YYYY-MM-DD..YYYY-MM-DD`); when set, the skill uses it exactly and skips the default
window. `client_filter` matches the start of the page title (case-insensitive). Omit both
for the default window (Monday → prior Mon–Fri; otherwise yesterday).

---

## Required secrets (GitHub → Settings → Secrets)

| Secret | What it's for |
|--------|--------------|
| `ANTHROPIC_API_KEY` | Claude — required by the Claude CLI |
| `NOTION_TOKEN` | Notion MCP server (`@notionhq/notion-mcp-server`) |
| `GDRIVE_CREDENTIALS_JSON` | Google Drive MCP server — OAuth client credentials JSON |
| `GDRIVE_TOKEN_JSON` | Google Drive MCP server — OAuth token JSON |
| `GCHAT_WEBHOOK` | GChat webhook URL — no MCP needed, just a POST |

All MCP tools (`notion-search`, `notion-fetch`, `notion-update-page`, `download_file_content`)
are called by Claude through the configured MCP servers — not direct API calls.

---

## Reading theme files

Each `themes/[theme_slug].md` file tells you:
- What the pattern is (one-line description)
- How many clients have surfaced it (`client_count`)
- Current status: `candidate` (1 client) → `emerging` (2) → `theme` (3+)
- Every occurrence with a direct link to the Notion meeting page, the verbatim quote, and the transcript timestamp

---

## Signal Taxonomy v2

Full documentation: [Signal Taxonomy — Notion](https://app.notion.com/p/hylyai/Signal-Taxonomy-3871db9ba44180f38268d6c6e1a7646b)
Definitions for each type are also in `config/taxonomy.json`.

12 signal types across 6 categories:

| Category | Signal types | Owner |
|----------|-------------|-------|
| Enablement | knowledge, skill, asset | CSM Ops |
| Communication | comms, positioning, response | CSM Ops |
| Operations | process | CSM Ops |
| Product | feature_gap, expectation, limit | PM |
| Competitive | competitor | EA + Sales |
| Relationship | positive | Marketing |
