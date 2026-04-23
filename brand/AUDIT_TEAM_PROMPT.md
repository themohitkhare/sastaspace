# Agent Teams audit prompt — SastaSpace

Paste one of these into a Claude Code session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` enabled. Best run on branch `brand-redesign` before merging to `main`.

---

## Main — 5-teammate full audit (recommended)

Five independent lenses, one consolidated report at the end. Each teammate has a distinct file scope so they don't collide. Auditors REPORT only; they do not fix.

```text
I want you to create an agent team of auditors to review the brand-redesign branch
of this repo before it merges to main. The work under audit spans brand/,
projects/landing/web/, projects/_template/web/, and design-log/003-brand-rollout.md.
The invariants the work must respect live in brand/BRAND_GUIDE.md — read that file
first and make sure every teammate reads it too.

Spawn exactly 5 teammates, each running in its own context with its own lens. Do
not fix anything: every teammate's job is to produce findings, not patches. At the
end, synthesise their findings into one prioritised report at
audit/BRAND_REDESIGN_AUDIT.md.

Teammates:

1. name: security
   charter: Security + auth + secrets + deps.
   scope: projects/landing/web (whole tree), proxy.ts, any Supabase/GoTrue
     integration, .env.example, infra/k8s secrets templates.
   look for: auth flow correctness (JWT handling, cookie flags, SSR session
     refresh via @supabase/ssr), RLS assumptions that break if the client
     spoofs a role, XSS/CSRF exposure in forms (including Turnstile-fronted
     contact), dep vulnerabilities (check package.json against known CVEs),
     secrets or tokens accidentally in committed files, overly broad
     .gitignore holes, and admin-route access control (see
     src/app/(admin)/admin/layout.tsx).

2. name: code-arch
   charter: Code quality + architecture + performance.
   scope: projects/landing/web/src (all .ts/.tsx), projects/_template/web/src.
     Do NOT duplicate work the security teammate owns.
   look for: TypeScript strictness + unsafe any, component decomposition
     (any file doing three jobs?), RSC vs client-component boundaries (is
     anything marked "use client" that shouldn't be?), coupling between
     brand primitives and shadcn semantic tokens (globals.css), hydration
     risks, bundle weight from next/font (are all three fonts justified?),
     image loading strategy, CLS risks, dead code (old generic "Project
     Bank" copy left behind anywhere?).

3. name: ui-brand
   charter: Visual parity with brand/landing-mockup.html + brand invariant
     enforcement.
   scope: projects/landing/web (whole app in the browser, both light and dark
     mode), all .tsx files that render UI, globals.css.
   look for: violations of brand/BRAND_GUIDE.md (§4 palette, §5 type, §6
     visual vocabulary, §9 "what the system is NOT"). Zero tolerance for:
     gradients, drop shadows, glows, ALL CAPS, Title Case in UI, font
     weights above 500, white (#ffffff) page backgrounds, sasta orange
     (#c05621) on body text. Also check: spacing parity vs the mockup at
     1440px and 375px (flag any drift > 2px), Devanagari sub-lines present
     on every major section, dark-mode paper/ink flip preserves hierarchy.

4. name: ux-a11y
   charter: UX + content voice + WCAG 2.1 AA.
   scope: every user-facing string and every interactive surface in
     projects/landing/web. brand/bio.md is the voice reference.
   look for: copy drift from bio.md (paraphrased Hindi is a bug; paraphrased
     hero copy is a bug), empty state and error microcopy in brand voice,
     keyboard reachability of every link and form control, visible focus
     rings (sasta ring token at 2px min), semantic HTML (correct h1→h2 order
     per section), aria-label accuracy on StatusChip and BrandMark, color
     contrast ≥4.5:1 on body text and ≥3:1 on large text IN BOTH MODES, any
     input that fails screen-reader labelling, motion-reduced behaviour (no
     jarring transitions even though no animation was added).

5. name: tests-build
   charter: Test coverage + build + lint + CI readiness.
   scope: projects/landing/web (entire package + any test files),
     projects/_template/web, package.json scripts, .github/workflows.
   look for: critical paths with zero test coverage (auth, admin gating,
     contact form validation, PostgREST fetch failure handling), any test
     runner at all (CLAUDE.md says vitest is the convention; is it wired
     up?), `npm run build` green on both landing and _template, `npx
     eslint .` green, TypeScript `tsc --noEmit` green, dead scripts in
     package.json, CI workflow at .github/workflows/deploy.yml still
     compatible with the changes (no script name drift).

Coordination rules:
- Every teammate MUST read brand/BRAND_GUIDE.md and design-log/003-brand-rollout.md
  before filing findings.
- Every finding MUST include: severity (P0/P1/P2), a single-line summary,
  file:line reference, short justification, suggested fix. No vague
  "consider refactoring" — be concrete.
- Severity bar:
    P0 = blocks merge (security hole, broken build, brand invariant violation,
         WCAG AA failure on body copy)
    P1 = should fix before launch (UX drift, thin test coverage, perf issue)
    P2 = nice-to-have (style nits, future-proofing)
- If two teammates would both report the same issue, the teammate whose scope
  owns it files it; the other adds a cross-reference ("see ui-brand #4").
- No file edits. This is a read-only audit. If you catch yourself wanting to
  fix something, add it as a P0/P1 finding with the proposed patch in the
  suggested-fix field instead.
- Teammates may message each other to coordinate scope boundaries. Use
  broadcast sparingly.

Final deliverable — you (the lead) produce it after every teammate is idle:
audit/BRAND_REDESIGN_AUDIT.md with these sections, in order:
  1. Summary — counts by severity, top 3 P0s, overall verdict (merge / block
     / block-with-conditions).
  2. Findings — all P0s first, then P1s, then P2s. Each finding in the
     format above. Group by teammate.
  3. Recommendations — concrete next steps, ordered.
  4. Appendix — what each teammate reviewed (file list), what they
     deliberately skipped.

Do not clean up the team until I've read the report and asked you to. If I
need to dispatch fixers, I'll tell you then.
```

---

## Quick variant — 3 teammates, ~70% of the coverage

Use when you want a faster, cheaper pass. Merges code+tests into one, ux+a11y into one, and keeps brand+security separate.

```text
Create an agent team of 3 auditors for the brand-redesign branch. Read
brand/BRAND_GUIDE.md first — invariants live there. Scope: brand/,
projects/landing/web/, projects/_template/web/. Auditors REPORT, they don't
fix. Output: audit/BRAND_REDESIGN_AUDIT.md with P0/P1/P2 findings.

1. name: brand-security
   scope: brand invariant enforcement + security review combined.
   look for: any violation of brand/BRAND_GUIDE.md §4–6 + §9, plus auth,
     secrets, dep vulns, admin-route gating.

2. name: engineering
   scope: code quality + types + build + lint + test coverage + perf.
   look for: TS strictness, RSC/client boundaries, bundle weight, `npm
     run build` + `eslint` + `tsc --noEmit` health, critical paths
     missing tests.

3. name: ux
   scope: voice + copy + a11y + WCAG AA + keyboard/screen-reader.
   look for: copy drift from brand/bio.md, WCAG contrast in both modes,
     focus rings, semantic HTML, aria-labels, empty/error microcopy.

Every finding must include severity, file:line, justification, and a
concrete suggested fix. Severity bar: P0 blocks merge; P1 before launch;
P2 nice-to-have. Do not fix anything. Do not clean up the team until I've
read the report.
```

---

## Optional hooks — enforce finding quality

Drop this in `.claude/hooks/TaskCompleted.sh` to block auditors from marking a
task complete without a properly-formatted finding. Exits with 2 to send
feedback and keep the teammate working.

```bash
#!/usr/bin/env bash
# TaskCompleted hook — enforce audit finding format
set -e
payload=$(cat)
# Expect the task to contain "severity:" and "file:" fields
if echo "$payload" | grep -qE '"name":"audit-'; then
  if ! echo "$payload" | grep -qE 'severity: *(P0|P1|P2)' \
     || ! echo "$payload" | grep -qE 'file: *[^[:space:]]+:[0-9]+'; then
    echo "Finding missing required fields (severity: P0|P1|P2, file:line). Fix and retry." >&2
    exit 2
  fi
fi
exit 0
```

Make it executable: `chmod +x .claude/hooks/TaskCompleted.sh`.

---

## Tips

- **Run the audit locally, not in Ruflo.** Agent Teams is a Claude Code native feature. Running it through Ruflo orchestration is possible but untested and overkill for a read-only review.
- **3–5 teammates is the sweet spot.** Docs recommend this range. 7+ starts diminishing returns and token costs climb linearly.
- **No file conflicts by construction.** Each teammate owns a distinct scope (security vs UI vs code, etc.) so they never edit the same file — that's agent-teams best practice.
- **Use split-pane mode if you have tmux or iTerm2.** Watching five panes at once is genuinely useful for audit work. Otherwise Shift+Down cycles through teammates in a single terminal.
- **Re-run the same prompt per release.** This is a standing audit template — use it before every merge to main after meaningful UI or auth work.
