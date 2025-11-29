# Cursor Commands for SastaSpace

This directory contains Cursor AI commands that augment the agentic team workflow.

## Agent Architecture Integration

The SastaSpace project uses an autonomous agentic team architecture with 5 agent personas:
- **PM-Agent**: Issue validation and management
- **Arch-Agent**: Architecture design
- **Code-Agent**: Feature implementation
- **Review-Agent**: Code review
- **QA-Agent**: Quality assurance

See `docs/AGENT_ARCHITECTURE.md` for complete documentation.

## Available Commands

### Development Commands (Code-Agent)

- **`create-pr.md`** - Generate PR descriptions when creating pull requests
- **`address-github-pr-comments.md`** - Fix code based on Review-Agent feedback
- **`run-all-tests-and-fix.md`** - Run full test suite and fix failures during development

### Review Commands (Manual/Pre-Commit)

- **`code-review-checklist.md`** - Manual code review checklist (Review-Agent handles this automatically in CI)
- **`light-review-existing-diffs.md`** - Quick pre-commit review of uncommitted changes
- **`security-audit.md`** - Manual security audit (QA-Agent runs Brakeman automatically in CI)

### Specialized Commands

- **`ux-audit.md`** - UI/UX audit against Apple Design Guidelines
- **`draft-release-notes.md`** - Generate release notes from git history

## Removed Commands

The following commands were removed as they're now handled by agent workflows:

- ~~`setup-new-feature.md`~~ - Replaced by Arch-Agent (architecture) + Code-Agent (implementation)
- ~~`triage-issues.md`~~ - Replaced by PM-Agent workflow (auto-validates issues)
- ~~`generate-prd.md`~~ - Replaced by PM-Agent issue templates (feature_request.yml)

## Usage

When acting as an agent persona, use the appropriate commands:

- **Code-Agent**: Use `create-pr.md`, `address-github-pr-comments.md`, `run-all-tests-and-fix.md`
- **Review-Agent**: Use `code-review-checklist.md` for manual reviews (automated checks run in CI)
- **QA-Agent**: Use `security-audit.md` for manual audits (Brakeman runs automatically in CI)

For general development, use any command as needed.

## Workflow Integration

These commands complement the automated agent workflows in `.github/workflows/agent_orchestration.yml`:

1. **Issue Creation** → PM-Agent validates (auto)
2. **Architecture Design** → Arch-Agent designs (auto or manual)
3. **Implementation** → Code-Agent uses commands here
4. **Code Review** → Review-Agent checks (auto) + manual review commands
5. **Quality Assurance** → QA-Agent runs CI (auto) + manual audit commands
