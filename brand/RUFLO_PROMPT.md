# Ruflo orchestration — SastaSpace brand redesign

Copy-paste ready. Run from the repo root (`sastaspace/`). Assumes the repo is cloned and `brand/REDESIGN_PLAN.md` is on disk.

---

## 1. One-time setup (skip if already done)

```bash
# from repo root
npx ruflo@latest init            # writes .ruflo/ and CLAUDE.md hooks
npx ruflo@latest mcp start &     # background MCP server for Claude Code integration
npx ruflo hive-mind init         # initialize the hive store
```

## 2. Recommended — hierarchical hive-mind swarm

This matches the plan: one strategic queen routes, specialist workers execute each task in order. Use this for the main run.

```bash
npx ruflo hive-mind spawn \
  --queen-type strategic \
  --topology hierarchical \
  --consensus byzantine \
  --agents "architect,frontend-coder,css-tokens-specialist,next-specialist,tester,code-reviewer,tech-writer" \
  --parallel \
  --memory collective \
  --checkpoint-after-task \
  "$(cat brand/RUFLO_OBJECTIVE.md)"
```

The objective is stored in `brand/RUFLO_OBJECTIVE.md` (below) so git tracks any edits and the command line stays short.

## 3. Alternative — explicit SPARC workflow (more ceremony, more oversight)

If you want each phase as a discrete checkpoint instead of one hive run:

```bash
# architecture review of the existing plan — should return "plan is sufficient, proceed"
npx claude-flow sparc run architect "Review brand/REDESIGN_PLAN.md against the current state of projects/landing/web/. Confirm the task order, flag any missed dependencies, and stop."

# implementation phase
npx claude-flow sparc run code "Execute Tasks 1 through 7 of brand/REDESIGN_PLAN.md. Commit per task on branch brand-redesign. Do not proceed past Task 7."

# test/validation phase
npx claude-flow sparc run tdd "Verify the acceptance criteria in brand/REDESIGN_PLAN.md section 4. Run npm run build and npx eslint . in projects/landing/web. Screenshot-compare http://localhost:3000 against brand/landing-mockup.html at 1440px and 375px. Report pass/fail per criterion."

# final wave
npx claude-flow sparc run code "Execute Tasks 8 and 10 of brand/REDESIGN_PLAN.md. Task 9 is optional — skip unless the tests in Task 8 require it. Open a PR."
```

## 4. Objective text (paste into `brand/RUFLO_OBJECTIVE.md` or pass inline)

See the sibling file **RUFLO_OBJECTIVE.md** — it's the full strategic prompt the queen consumes. Keeping it as a standalone file lets you edit without re-escaping quotes.

## 5. Monitoring

```bash
npx ruflo hive-mind status       # alive queens + workers, current task
npx ruflo hive-mind metrics      # throughput, cost so far
npx ruflo hive-mind memory       # what the collective has learned
npx ruflo hive-mind sessions     # list runs; resume with --resume <id>
```

## 6. When it stops

The queen will pause at the checkpoints defined in the objective (after Task 7; before Task 9; before opening the PR). Resume with `npx ruflo hive-mind resume <session-id>` or kill with `npx ruflo hive-mind stop`.
