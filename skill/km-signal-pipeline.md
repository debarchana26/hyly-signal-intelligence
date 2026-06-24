---
name: km-signal-pipeline
description: "Daily client call signal pipeline. Reads recent Hyly.AI client calls from Notion MeetingDiary, fetches VTT transcripts from Google Drive, extracts signals using Signal Taxonomy v2, applies revenue weighting, routes to 3 GChat feeds, and writes theme files to Git. Trigger on: 'run signal pipeline', 'process today's calls', 'process this week's calls', scheduled daily cron."
---

# km-signal-pipeline

## Config (read before every run)

- `config/call-filter.json` — which Notion pages to process
- `config/taxonomy.json` — signal type → category, owner, feeds
- `config/mrr-thresholds.json` — MRR threshold and severity bump rules
- `config/gchat-templates.json` — the GChat card JSON templates (the ONLY source for cards posted to Google Chat)

## Constants

```
MEETING_DIARY_DB  = f22d80836d1d4759a1c0c133a4cce8c9
DEAL_STRATEGY_DB  = 1a51db9ba44180969722c19633401f15

GCHAT_WEBHOOK = https://chat.googleapis.com/v1/spaces/AAQAyF9D3W8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=5r-XFkyPHwpzvohwYqzrP43fYaw7eszKBMpxBJDT90U

TEST_MODE = true
```

---

## Step 1 — Date window + call query

**Date window:**
- Monday: prior Mon–Fri
- All other days: yesterday
- No results found: expand back 1 day per iteration, max 7 days
- All calls in window already have `Added to Google Chat = true`: print "Nothing new" and stop

**Query MeetingDiary** using `notion-search`:
- `Status` = values in `call-filter.json → status`
- `Meeting Type` = values in `call-filter.json → meeting_type_include`
- `Added to Google Chat` = false
- `Meeting Date` within date window
- `[NEW] GDrive Transcript URL` or `GDrive Transcript URL` is not empty

**Extract from each page:**
- `meeting_page_id` — Notion page ID
- `notion_page_url` — full Notion URL (stored in every theme occurrence)
- `client` — from page title (`Discovery` field, format: `ClientName.YYYY.MM.DD`)
- `call_date` — from `Meeting Date` field
- `meeting_type` — from `Meeting Type` field
- `hyly_lead` — from `Hyly Lead` person field (extract display name)

---

## Step 2 — MRR lookup

For each call:
1. Read `📈 sdb.DealStrategy` relation from the MeetingDiary page
2. Fetch the related DealStrategy record
3. Read the MRR field

- MRR > `mrr-thresholds.json → mrr_high_threshold` → `mrr_tier = high`
- Relation missing, record not found, or MRR field empty → `mrr_tier = standard`

---

## Step 3 — Transcript fetch

Check transcript URL fields in priority order from `call-filter.json → transcript_fields_priority`:
1. `[NEW] GDrive Transcript URL`
2. `GDrive Transcript URL`

Use the first non-empty value.

**Extract File ID** from URL: `https://drive.google.com/file/d/[FILE_ID]/view`

**Download:** `mcp__51a97106-00b1-4ed9-af0f-46226519d15b__download_file_content` → base64 → decode to VTT text

**If fetch fails or both fields empty:**
- Log in run summary: `[client] [call_date] — transcript not accessible`
- Leave `Added to Google Chat = false`
- Skip this call, continue to next

---

## Step 4 — Signal analysis (single pass, max 6 signals per call)

Read routing from `config/taxonomy.json`.

For each signal extract:
- `signal_type` — one of the 12 types in taxonomy.json
- `category` — from taxonomy.json (do not derive independently)
- `theme_slug` — format: `[signal-type]-[category]-[descriptive-name-kebab-case]`
  - Descriptive name: 3–5 words, kebab-case, specific not generic
  - Example: `knowledge-enablement-blast-segmentation-by-building`
  - Check `themes/` directory first — if a matching theme file exists, use its exact slug
- `verbatim_quote` — 50–120 chars, include speaker name and transcript timestamp: `"[Speaker, HH:MM] quote text"`
- `context` — 1 sentence explaining what the observation reveals
- `severity_raw` — based on content: use severity scale from `mrr-thresholds.json → severity_scales` for the target feed
- `positive_subtype` — if `positive`: one of `advocacy | endorsement | expansion_intent | trust_signal`

**Detect all 12 types:**
1. `knowledge` — client unaware of platform capability
2. `skill` — rep misses feature opportunity or frames incorrectly
3. `asset` — missing training material or guide
4. `response` — rep gives inconsistent answer to recurring question
5. `comms` — client discovers limitation live on call
6. `process` — broken pre/post-training workflow
7. `feature-gap` — client requests missing feature
8. `expectation` — client had wrong product expectation
9. `limit` — client hits hard platform constraint
10. `competitor` — competitor named on call
11. `positive` — advocacy / endorsement / expansion intent / trust signal
12. `positioning` — rep struggles with competitive or change messaging

---

## Step 5 — Revenue weighting

For each signal where `mrr_tier = high`:
Apply bump rules from `mrr-thresholds.json → severity_bump_when_mrr_high` per feed.
Set `severity_final`.

---

## Step 6 — Idempotency check

For each signal:
1. Check if `themes/[theme-slug].md` exists
2. If it exists, check the Occurrences table for a row matching this `notion_page_url`
3. Match found → skip this signal (already logged), continue

---

## Step 7 — Route to feeds

Feeds for each signal type come from `config/taxonomy.json → feeds`.

**Card format — REQUIRED:** Every card posted to Google Chat (any feed) MUST be built
from `config/gchat-templates.json`. This is the single source of truth for card layout —
look up the matching template by name (`client_meeting_card`, `product_digest_critical`,
`weekly_product_digest`, `positive_signal`, etc.), fill its placeholders, and POST that
JSON to the `GCHAT_WEBHOOK`. Do NOT hand-build card JSON or invent a different layout.
The text blocks below are field-mapping references only — the actual payload comes from
the template file.

### client_meeting_feed (all calls, top 3 signals per call by severity)

```
📋 [Client] — [Meeting Type] — [YYYY-MM-DD] — [Hyly Lead]

🔴 Act Now: [theme_slug] — [context]
🟡 Watch: [theme_slug] — [context]
🟢 Healthy: [theme_slug] — [context]

Source: [Notion URL] — [HH:MM]
```

### product_digest_feed

**Immediate (Critical only — any day):**
```
🚨 Critical Gap Alert — [Client] — [YYYY-MM-DD] — [Hyly Lead]
Signal: [theme_slug]
MRR: $[X]/month
Severity: Critical — [reason]
"[verbatim_quote]"
Source: [Notion URL] — [HH:MM]
Action required: PM to confirm owner and response plan before end of day.
```

**Monday weekly digest** — compiled from `themes/` folder by `weekly-digest.yml` (not this job).

### marketing_feed (per positive signal)

```
🟢 Positive Signal — [Client] — [YYYY-MM-DD] — [Hyly Lead]
Subtype: [advocacy | endorsement | expansion_intent | trust_signal]
MRR: $[X]/month
"[verbatim_quote]"
Source: [Notion URL] — [HH:MM]
Suggested action: [advocacy→case study | endorsement→social proof | expansion_intent→alert CSM+AE | trust_signal→relationship tracker]
```

**TEST_MODE = true:** Print all cards to chat with `[TEST — NOT SENT]`. Do not call webhook.

---

## Step 8 — Write theme files

For each signal processed (not skipped as duplicate):

**If `themes/[theme-slug].md` does not exist** — create it:

```markdown
---
theme_slug: [theme-slug]
signal_type: [signal_type]
category: [category]
owner: [owner from taxonomy.json]
status: candidate
client_count: 1
first_seen: [call_date]
last_seen: [call_date]
---

[One-line description of what this theme represents.]

## Occurrences

| Client | Date | Notion Page | Quote | Timestamp |
|--------|------|-------------|-------|-----------|
| [client] | [call_date] | [Meeting]([notion_page_url]) | "[verbatim_quote]" | [HH:MM] |
```

**If `themes/[theme-slug].md` exists** — append a row to the Occurrences table and update frontmatter:
- `client_count` += 1
- `last_seen` = call_date
- `status`: 1 client → `candidate`, 2 clients → `emerging`, 3+ clients → `theme`

---

## Step 9 — Update MeetingDiary

Transcript processed successfully → set `Added to Google Chat = true` on the Notion page.
Transcript not accessible → leave `false`.

---

## Monday: weekly digest

Handled by `weekly-digest.yml` workflow after daily ingest completes.
Reads `themes/` folder, filters signals from past 7 days in Occurrences tables,
compiles digest card, posts to `product_digest_feed`.

---

## Run summary

```
km-signal-pipeline — [YYYY-MM-DD HH:MM] — Mode: TEST/LIVE
Calls processed: [N] | Skipped (no transcript): [N]
Signals: [N] | client_meeting_feed: [N] | product_digest_feed: [N] | marketing_feed: [N]
New themes: [N] | Updated themes: [N] | Duplicates skipped: [N]
MeetingDiary updated: [N]
```

---

## Error handling

| Error | Action |
|---|---|
| Transcript fetch fails | Log in summary, skip call, leave Added to Google Chat = false |
| Both GDrive URL fields empty | Same as above |
| MRR missing or relation not found | Default mrr_tier = standard, continue |
| Duplicate signal (theme file match) | Skip post, do not update theme file |
| Notion query error | Skip call, log in summary, continue |
| GChat webhook error (LIVE mode) | Log in summary, do not mark call as processed |
