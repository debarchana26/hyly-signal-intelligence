# CLAUDE.md — km-signal-intelligence

This repo is the Hyly.AI client call signal pipeline. Claude is the pipeline engine.
Every run reads from Notion (source data only), writes theme files to this repo, and posts cards to GChat.

---

## Before every run

Read these three files in order before taking any action:

1. `config/call-filter.json` — defines which Notion pages to query
2. `config/taxonomy.json` — defines signal type → category, owner, and feeds
3. `config/mrr-thresholds.json` — defines MRR threshold and severity bump rules

Do not hardcode any values that exist in these files. If a routing decision is not in taxonomy.json, stop and flag it rather than guessing.

---

## Theme slug rules

A theme slug must follow this exact format:
```
[signal-type]-[category]-[descriptive-name-kebab-case]
```

- `signal-type`: one of the 12 types in taxonomy.json
- `category`: taken from taxonomy.json for that signal type — do not derive independently
- `descriptive-name`: 3–5 words, kebab-case, specific enough to distinguish from other themes of the same type

Before generating a new slug, scan `themes/` for an existing file that matches the observation. If a match exists, use its exact slug — do not create a variant.

Examples of correct slugs:
- `knowledge-enablement-blast-segmentation-by-building`
- `feature-gap-product-renewal-drip-automation`
- `competitor-competitive-elise-ai-coexistence`
- `positive-relationship-hines-fat-village-expansion-intent`

Examples of incorrect slugs (do not use):
- `knowledge--blast-segmentation` (missing category, double dash)
- `feature-gap-renewal-drip` (missing category)
- `knowledge-blast-email-building-segmentation` (variant of existing slug)

---

## Writing theme files

Every theme file lives in `themes/[theme-slug].md`.

When creating a new theme file, use the template in `skill/km-signal-pipeline.md → Step 8` exactly.

When updating an existing theme file:
- Append one row to the Occurrences table
- Update `client_count`, `last_seen`, and `status` in frontmatter
- Do not rewrite or reformat any existing rows
- Status promotion rules: 1 client = candidate, 2 clients = emerging, 3+ clients = theme

The Notion page URL must appear in every Occurrences row. This is the link back to the source transcript.

---

## Hyly Lead

`Hyly Lead` is a person field in Notion. Extract the display name (first + last). If the field has multiple people, use the first. If empty, use `—`.

---

## TEST_MODE

When `TEST_MODE = true` in the skill constants:
- Print all GChat cards to chat with `[TEST — NOT SENT]` prefix
- Do not call the GChat webhook
- Do write theme files to Git normally
- Do set `Added to Google Chat = true` in Notion normally

Announce TEST_MODE at the start of every run: "Running in TEST MODE — cards will not be posted to GChat."

---

## What NOT to do

- Do not write to any Notion database other than setting `Added to Google Chat = true` on MeetingDiary pages
- Do not create a Notion Signal Log entry — the theme files in `themes/` are the signal log
- Do not post to the GChat webhook when TEST_MODE = true
- Do not generate a theme slug that is a variant of an existing slug in `themes/`
- Do not infer routing rules — read taxonomy.json
- Do not skip the idempotency check (Step 6 in the skill)
- Do not mark a call as processed (`Added to Google Chat = true`) if the transcript was not accessible or the GChat post failed in LIVE mode

---

## Git commits

After each run, commit changes to `themes/` and `digests/` with message:
```
signal: YYYY-MM-DD [N calls] [N signals] [N themes updated]
```

---

## Iteration history & file policy

- **`history.md` is the canonical iteration record.** Every commit that changes pipeline
  behavior (anything under `skill/`, `config/`, or `.github/workflows/`) MUST add a dated
  entry to the `history.md → Change log` in the same commit. Do not rewrite past entries.
- **Never add `.py` files to this repo.** The pipeline engine is the Claude skill at
  `skill/km-signal-pipeline.md`, not Python. `.py`/`__pycache__` are blocked by
  `.gitignore` and the pre-commit hook in `.githooks/`.
- A fresh clone must run `git config core.hooksPath .githooks` once to enable the hook.

---

## Run summary

Always print the run summary at the end, even if no signals were found. Format is in `skill/km-signal-pipeline.md → Run summary`.
