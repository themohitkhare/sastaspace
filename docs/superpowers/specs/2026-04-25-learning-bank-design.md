# Learning Bank — Design

**Date:** 2026-04-25
**Owner:** Mohit Khare
**Status:** Draft, pending user review

## Problem

Across many AI coding sessions (Claude Code, Cursor) over months, the user has accumulated:

- preferences and feedback ("don't do X", autonomy level, style)
- technical decisions and their rationale (why Redis, why Browserless, why we pivoted)
- anti-patterns and corrections (things AI got wrong, hallucinated, or had to be told twice)
- domain knowledge not in code (prod box names, cred locations, who-owns-what)
- workflow patterns that worked (deploy steps, debug recipes)
- tool / library / model guidance

Today this lives only inside individual transcript files. Future agents in new sessions have to relearn all of it from scratch. The user wants a one-shot extraction-and-curation pass that distils these learnings into a persistent "learning bank" available to future AI agents.

## Goals

- Mine all available transcripts (Claude Code + Cursor) once, comprehensively.
- Produce a raw harvest (JSONL) and a curated, human-approved bank (Markdown).
- Make the curated bank available to future agents in two tiers: always-on for universal items and on-demand for the long tail.
- Keep it cheap to update or discard later — no fragile recurring pipeline.

## Non-goals

- Not building a recurring extraction pipeline. This is one-shot; a future re-run is a manual repeat of the same stages.
- Not building a search / embeddings / MCP retrieval service. The on-demand tier is a Skill the model loads as a unit.
- Not extracting code patterns, file paths, or architecture facts that can be re-derived from the current repo. Memory is for what is *not* in code.
- Not modifying the existing per-project auto-memory system at `~/.claude/projects/<project>/memory/`. The learning bank is cross-project and lives separately.

## Sources in scope

| Source | Location | Volume |
|---|---|---|
| Claude Code transcripts | `~/.claude/projects/*/[uuid].jsonl` | ~175 sessions, 121 MB |
| Cursor chats | `~/Library/Application Support/Cursor/User/{workspaceStorage/*,globalStorage}/state.vscdb` (SQLite) | 5 workspaces + 1 global |
| Existing distilled memory | `~/.claude/projects/<project>/memory/*.md` | 15 entries (already curated; treated as seeds, not re-extracted from transcripts) |

## Architecture — three stages

```
1. EXTRACT (parallel)        2. CURATE (interactive)      3. PUBLISH
   inventory + clean +          dedupe / cluster /           write curated MD,
   dispatch parallel            keep-edit-drop /             a Skill, and an
   subagents                    tier each item               always-on block
```

No long-lived scripts. Bash one-liners + parallel `Agent` dispatches + `Write`. The pipeline runs once.

### File layout

```
~/.claude/learnings/
├── manifest.jsonl                              # one line per source session
├── extractions/<session-id>.jsonl              # per-session subagent output
├── raw/{feedback,decisions,antipatterns,
│        domain,workflows,tooling}.jsonl        # aggregated per category
└── curated/{category}.md                       # keepers, after curation

~/.claude/skills/learning-bank/SKILL.md         # on-demand consumption
~/.claude/CLAUDE.md  (appended marked section)  # always-on tier
```

## Stage 1 — Extract

### Inventory

```bash
ls ~/.claude/projects/*/[a-f0-9]*.jsonl                  # Claude Code transcripts

for db in \
  ~/Library/Application\ Support/Cursor/User/workspaceStorage/*/state.vscdb \
  ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb; do
  sqlite3 "$db" \
    "SELECT key, value FROM cursorDiskKV
       WHERE key LIKE 'composerData:%' OR key LIKE 'bubbleId:%';"
done
```

The Cursor SQLite schema is undocumented and may differ between versions. Inspect one DB first, confirm the table and key prefixes, then run for all five. If the schema is different, adapt the query before proceeding.

Each found session gets a line in `manifest.jsonl`: `{id, tool, project, path, date, size}`.

### Pre-filter to conversational text

Claude Code transcripts contain large `tool_use` and `tool_result` payloads that are not useful for extracting learnings. Per session, pre-filter:

```bash
jq -r 'select(.type=="user" or .type=="assistant")
       | {ts, type, text: ([.message.content[]? | select(.type=="text") | .text] | join("\n"))}
       | select(.text != "")' \
  session.jsonl > /tmp/cleaned/<session>.jsonl
```

This keeps user prompts and assistant text/rationale, drops tool I/O. Expected reduction: 10–50× per session.

For Cursor, dumped JSON values are already mostly text — light cleanup only.

### Dispatch

- ~200 cleaned sessions total.
- ~15 sessions per subagent → ~13 parallel `Agent` dispatches in 1–2 waves.
- Each subagent gets: list of session paths, the 6-category taxonomy with definitions, the output schema, and the extraction prompt.

### Extraction prompt (load-bearing)

> Read these sessions. Extract anything that future AI agents working with this user should know to avoid relearning. For each finding, classify into one of `{feedback, decisions, antipatterns, domain, workflows, tooling}`. Quote the evidence verbatim (1–3 sentences). Set `confidence` high / medium / low. Be liberal — duplicates are fine, we'll dedupe later. Skip ephemeral session-only context (current task progress, intermediate state) and anything that is already obvious from the code or git history.

### Output schema (one line per learning)

```json
{
  "category": "feedback | decisions | antipatterns | domain | workflows | tooling",
  "summary": "one-line gist",
  "body": "fuller explanation including the WHY",
  "evidence": "verbatim quote, 1-3 sentences",
  "source": {
    "tool": "claude-code | cursor",
    "project": "<inferred>",
    "session": "<filename or session id>",
    "date": "YYYY-MM-DD"
  },
  "confidence": "high | medium | low"
}
```

The parent (orchestrator) collects subagent outputs and appends each line to the matching `raw/{category}.jsonl`.

### Existing memory as seed

The 15 entries in `~/.claude/projects/<project>/memory/` are already-curated learnings. Read once, normalize to the schema, append to `raw/` with `confidence: high`, `source.tool: existing-memory`. They become the recall floor — anything in existing memory must reappear in the curated bank.

## Stage 2 — Curate (interactive)

After extraction we expect a few thousand raw candidates total across all categories (rough estimate: ~200 sessions × ~10 candidates each), with heavy duplication. The curation session is conversational, not automated.

For each category:

1. **Cluster** near-duplicates by summary similarity. Present clusters of 3–5 similar candidates with a proposed merged version using the strongest evidence.
2. **User decides per cluster:** `keep` / `edit` / `drop`. Default to keep if unsure.
3. **Tier each kept item:**
   - `always-on` — preferences, autonomy/style, critical anti-patterns. Hard cap: **~50 lines / ~800 tokens** in `CLAUDE.md`.
   - `on-demand` — decisions, domain, workflows, tooling, long-tail anti-patterns.

Expected outcome: ~1,000–2,000 raw candidates → ~50–100 curated entries total across all categories. Estimated curation time: 45–90 min for the full pass; can be split across sittings.

## Stage 3 — Publish

Three idempotent writes:

### 3a. Per-category curated Markdown

`~/.claude/learnings/curated/{category}.md` — each entry:

```markdown
### <summary>

<body — explanation including WHY and WHEN it applies>

<details><summary>evidence</summary>

> "<verbatim quote>"

— `<source.tool>` / `<source.project>` / `<source.date>`

</details>
```

These six files are the source of truth; the skill and CLAUDE.md tiers point at or inline this content.

### 3b. On-demand Skill

`~/.claude/skills/learning-bank/SKILL.md`:

- Frontmatter `description` triggers invocation when "starting a non-trivial task, making technical decisions, or working in unfamiliar areas for this user."
- Body: brief index + inlined content of all six curated MDs.
- If the file grows past ~600 lines, split into one skill per category.

### 3c. Always-on block in `CLAUDE.md`

Append a clearly-marked block to `~/.claude/CLAUDE.md`:

```
<!-- BEGIN learning-bank:always-on -->
... ~50 lines of universal preferences + critical anti-patterns ...
<!-- END learning-bank:always-on -->
```

Markers make the block safe to regenerate later without clobbering hand-written content. The block is regenerated by replacing the content between markers.

## Validation

After publish:

- **Recall sanity check** — every existing `memory/` entry must appear in the curated bank. If anything is missing, the extraction prompt was too narrow; rerun that category's extraction.
- **Evidence spot check** — sample 10 curated entries, confirm the `evidence` quote appears verbatim in the cited session file.
- **Live test** — open a fresh Claude Code session, ask "what do you know about my preferences and prior decisions?". Confirm the skill / CLAUDE.md content is reachable and the model can paraphrase it.

## Risks and call-outs

- **Cursor SQLite schema undocumented** — inspect one DB first; adapt the dump query before running across all five workspaces.
- **Pre-filter may drop useful context** — assistant text blocks are kept, but if rationale is buried in tool inputs we will lose it. Mitigation: if a category looks under-recalled, broaden the jq filter for that re-run.
- **Stale learnings** — point-in-time. The `source.date` field lets future curation runs flag or expire entries older than N months.
- **Always-on bloat** — strict 50-line cap; surplus universal candidates demote to on-demand.
- **Token cost** — one-shot brute-force LLM extraction on ~3–5M tokens of cleaned content. Acceptable per user direction; not amortizable since this is one-shot.
- **One-shot, not recurring** — by user request. Re-running is a manual rerun of stages 1+2.

## Open questions for user review

- Are the six categories right, or should any be merged / split?
- Is `~/.claude/learnings/` the right home, or do you want it inside the sastaspace repo so it's source-controlled?
- Should the always-on block append to `~/.claude/CLAUDE.md`, or to a separate `~/.claude/learnings.md` that you manually `@`-include?
