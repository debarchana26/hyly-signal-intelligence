# Iteration History — km-signal-intelligence

This file is the single record of how the signal pipeline has evolved. It replaces the
ad-hoc collection of versioned Python prototypes (`*_v2.py`, `*_final.py`, `*_strict.py`,
etc.) that previously lived in the repo root.

**Rules (enforced — see `CLAUDE.md → Iteration history & file policy`):**
- The pipeline engine is the **Claude skill** at `skill/km-signal-pipeline.md`, not Python.
- **No `.py` files** are committed to this repo (blocked by `.gitignore` + pre-commit hook).
- **Every iteration / commit that changes pipeline behavior must add an entry below.**

---

## Architecture (current)

The live pipeline is Claude-driven. Both GitHub Actions workflows install the Claude CLI
and run the skill:

```
claude --print --dangerously-skip-permissions "Run the km-signal-pipeline skill."
```

- `skill/km-signal-pipeline.md` — pipeline spec Claude executes (the engine)
- `config/*.json` — `call-filter`, `taxonomy`, `mrr-thresholds` (source-of-truth routing)
- `themes/` — the signal log (one file per theme)
- `digests/` — generated digests
- `.github/workflows/daily-ingest.yml`, `weekly-digest.yml` — schedulers

---

## Legacy Python prototypes (removed 2026-06-24)

Before the Claude-skill architecture, the pipeline was prototyped as standalone Python
scripts that called the Notion / Google Drive / GChat APIs directly. These were superseded
in full and removed from the working tree (still recoverable via git history). Summarized
here so the iteration history is preserved.

### 2026-06-23 — initial Python prototyping (direct API)
| File | Role |
|---|---|
| `test_notion.py` | Probe Notion API availability; describe required env/setup |
| `test_notion_connection.py` | Verify Notion connection + MeetingDiary DB access (used `notion_client`) |
| `test_query.py` | Test querying the DB via the search method |
| `km_signal_pipeline.py` | First implementation, using the `notion_client` library; UUID-formatting fixes |
| `km_signal_pipeline_v2.py` | Rewrite onto direct REST (`requests`) instead of `notion_client` |
| `km_signal_pipeline_final.py` | "Final working" pass on the requests-based pipeline |
| `km_signal_pipeline_complete.py` | Added Google Drive transcript fetching (base64/regex handling) |

### 2026-06-24 — feature iterations, then deprecation
| File | Role |
|---|---|
| `km_signal_pipeline_v3.py` | Added notification rules |
| `km_signal_pipeline_strict.py` | Added guardrails + type hints (`typing`) |
| `km_signal_pipeline_final_v2.py` | Proper GChat card JSON formatting |
| `check_all_calls.py` | Utility to list all available calls in MeetingDiary |
| `sample_daily_digest.py` | Generators for sample GChat cards (demo of card formats) |
| `post_sample_cards.py` | Post the sample cards to GChat (imports `sample_daily_digest`) |
| `weekly_product_digest.py` | Weekly aggregation of the past week's signals |

**Why removed:** the pipeline moved to the Claude-skill model
(`skill/km-signal-pipeline.md` driven by the Claude CLI in GitHub Actions). All routing
logic now lives in `config/*.json` and the skill, making the Python scripts redundant.

> ⚠️ Security note: some removed scripts contained a hardcoded Notion token. The token
> must be rotated in Notion; it remains in git history until the history is scrubbed.

---

## Change log (going forward)

Add a new dated entry for every behavior-affecting change. Keep entries terse.

### 2026-06-24 — consolidate history, remove Python prototypes
- Removed all 14 legacy `.py` prototypes + `__pycache__/` from the working tree.
- Created this `history.md` as the canonical iteration record.
- Added `.gitignore` (`*.py`, `__pycache__/`) and a pre-commit hook to keep `.py` files
  out and remind to update `history.md`.
- Documented the file policy in `CLAUDE.md`.

### 2026-06-24 — taxonomy corrections
- Renamed signal type `gap` → `feature-gap` (clearer). Migrated the 2 existing theme
  files (`feature-gap-product-*.md`) and updated their `theme_slug`/`signal_type`
  frontmatter; updated slug examples in `CLAUDE.md` and skill Step 4.
- Enablement signal types (`knowledge`, `skill`, `asset`) owner changed `KM` → `CSM Ops`.
- Moved `response` from the `enablement` category to `communication` (owner `CSM Ops`).
- Updated the README routing/owner tables to match.

### 2026-06-25 — explicit date range, taxonomy definitions, rule docs
- **Skill Step 1 — date-range bug fix:** the skill now honors explicit `Date range:` and
  `Client filter:` inputs passed from `daily-ingest.yml`, instead of always computing the
  default window. Single date or `YYYY-MM-DD..YYYY-MM-DD` range; no auto-expand when given.
  Clarified there is no cap on calls processed ("top 3" is signals per call, not calls) and
  that only `Recent Client Meeting` pages are processed (never `Upcoming`).
- **taxonomy.json:** added a `definition` for each of the 12 signal types; made it the
  authoritative source for type boundaries (skill Step 4 now points to it).
- **Skill Steps 4/5/7 — made implicit rules explicit:** added the content severity rubric,
  documented revenue promotion as the only promotion path, defined how a Critical Gap is
  selected, and defined how the top-3 client-meeting signals are ranked.
- **weekly-digest.yml:** fixed stale signal type `gap` → `feature-gap`.
- **Removed `setup_pipeline.sh`** — legacy Python setup that contradicted the no-Python /
  Claude-skill policy. Real setup (enable git hooks) now documented in README.
- **README:** rewrote with a complete architecture diagram, a description of every file,
  setup/triggering, and the selection & promotion rules.

### 2026-06-24 — single GChat card template
- Removed the redundant `config/gchat-card-templates.json` (static 3-slot version).
- `config/gchat-templates.json` (dynamic, handles N signals) is now the sole card source.
- Skill Step 7 + Config section now require all GChat cards to be built from
  `config/gchat-templates.json`.

### 2026-06-26 — theme slug convention switched to snake_case
- **New convention:** `[signal]_[category]_[descriptive_name]` — every hyphen in a theme slug
  is now an underscore (was `[signal-type]-[category]-[descriptive-name-kebab-case]`).
- Renamed all 14 existing `themes/*.md` files (`-` → `_`) and updated each `theme_slug` frontmatter
  value to match its new filename.
- **taxonomy.json:** renamed the only hyphenated signal type `feature-gap` → `feature_gap` so the
  slug, the taxonomy key, and the `signal_type` frontmatter all stay consistent. Updated the
  `signal_type` value in the 2 `feature_gap_product_*.md` files.
- Propagated `feature-gap` → `feature_gap` everywhere it is referenced as a signal type:
  `weekly-digest.yml` digest filter, `README.md` (feeds/routing tables, Critical Gap rule, diagram),
  and `feature-requests.md` (ledger wording + the 2 slug rows).
- Updated convention docs and placeholders in `CLAUDE.md` and `skill/km-signal-pipeline.md`
  (`kebab-case` → `snake_case`, `[theme-slug]` → `[theme_slug]`, example/incorrect slugs).
