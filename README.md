# hyly-signal-intelligence

Signal pipeline for Hyly.AI client calls. Reads transcripts from Notion MeetingDiary, extracts intelligence using Signal Taxonomy v2, routes to 3 GChat feeds, and builds a compounding theme registry in this repo.

---

## Architecture

```
Notion MeetingDiary (source — read only)
        ↓
  km-signal-pipeline (Claude skill)
        ↓
  ┌─────────────────────────────┐
  │  themes/[theme-slug].md     │  ← compounding wiki layer
  │  digests/YYYY-WW.md         │  ← weekly compiled digest
  └─────────────────────────────┘
        ↓
  GChat feeds (3 channels)
```

**Notion is read-only** except for one write: `Added to Google Chat = true` on each processed MeetingDiary page.

**Git is the signal log.** Theme files are the durable, cross-client intelligence record. Every occurrence links back to its Notion meeting page.

---

## Feeds

| Feed | Audience | Cadence | Signal types |
|------|----------|---------|--------------|
| `client_meeting_feed` | Senior leaders | Daily — 3 signals per call | All 12 types |
| `product_digest_feed` | PM & EA | Critical gaps same-day; weekly digest Monday | gap, limit, expectation |
| `marketing_feed` | Marketing | Per positive signal | positive |

---

## Repo structure

```
config/
  call-filter.json        Which Notion pages qualify for processing
  taxonomy.json           Signal type → category, owner, feeds
  mrr-thresholds.json     MRR tier threshold and severity bump rules

skill/
  km-signal-pipeline.md   Pipeline spec (steps 1–9, card formats, error handling)

themes/
  [theme-slug].md         One file per named theme. Frontmatter + Occurrences table
                          with Notion page links. Updated on every run.

digests/
  YYYY-WW.md              Weekly compiled digests posted to product_digest_feed

.github/workflows/
  daily-ingest.yml        Runs daily Mon–Fri. Triggerable via GitHub Actions API.
  weekly-digest.yml       Runs Monday morning after daily ingest.

CLAUDE.md                 Behavioral spec for Claude running in this repo.
README.md                 This file.
```

---

## Triggering

### Scheduled
- Daily ingest: Mon–Fri at 09:00 UTC
- Weekly digest: Monday at 10:00 UTC (after daily ingest)

### Manual via GitHub UI
Actions → Daily Signal Ingest → Run workflow

### Manual via API (call from other systems)
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/hylyai/hyly-signal-intelligence/actions/workflows/daily-ingest.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "date_range": "2026-06-23",
      "client_filter": "Hines"
    }
  }'
```

`date_range` and `client_filter` are optional. Omit both for the default window.

---

## Required secrets (GitHub → Settings → Secrets)

| Secret | What it's for |
|--------|--------------|
| `ANTHROPIC_API_KEY` | Claude — required by `claude-code-action` |
| `NOTION_TOKEN` | Notion MCP server (`@notionhq/notion-mcp-server`) |
| `GDRIVE_CLIENT_ID` | Google Drive MCP server |
| `GDRIVE_CLIENT_SECRET` | Google Drive MCP server |
| `GDRIVE_REFRESH_TOKEN` | Google Drive MCP server (use existing OAuth refresh token) |
| `GCHAT_WEBHOOK` | GChat webhook URL — no MCP needed, just a POST |

All MCP tools (`notion-search`, `notion-fetch`, `notion-update-page`, `download_file_content`)
are called by Claude through the configured MCP servers — not direct API calls.

---

## Reading theme files

Each `themes/[theme-slug].md` file tells you:
- What the pattern is (one-line description)
- How many clients have surfaced it (`client_count`)
- Current status: `candidate` (1 client) → `emerging` (2) → `theme` (3+)
- Every occurrence with a direct link to the Notion meeting page, the verbatim quote, and the transcript timestamp

---

## Signal Taxonomy v2

Full documentation: [Signal Taxonomy — Notion](https://app.notion.com/p/hylyai/Signal-Taxonomy-3871db9ba44180f38268d6c6e1a7646b)

12 signal types across 6 categories:

| Category | Signal types | Owner |
|----------|-------------|-------|
| Enablement | knowledge, skill, asset, response | KM |
| Communication | comms, positioning | CSM Ops |
| Operations | process | CSM Ops |
| Product | gap, expectation, limit | PM |
| Competitive | competitor | EA + Sales |
| Relationship | positive | Marketing |
