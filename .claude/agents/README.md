# Project subagent definitions

These Markdown files define reusable subagent roles that can be spawned via the `Agent` tool or as teammates in an agent-team (see https://code.claude.com/docs/en/agent-teams).

## Origin

Twelve of the files here are adapted from the MIT-licensed **ruvnet/ruflo** agent library:

- Upstream: https://github.com/ruvnet/ruflo
- Pinned commit: `01070ede81fa6fbae93d01c347bec1af5d6c17f0` (2026-04-11)
- License: MIT (see upstream `LICENSE`)
- Imported on: 2026-04-23

### Changes from upstream

All imported files had their `## MCP Tool Integration` sections removed, since those referenced `mcp__claude-flow__*` tools that no longer exist in this project after the ruflo MCP server was uninstalled. A few prose phrases ("via memory", "via MCP memory tools", "coordinate through memory") were rewritten to generic teammate-coordination wording.

### Mapping (ruflo source → this repo)

| Upstream path | Installed as |
| --- | --- |
| `.claude/agents/core/coder.md` | `coder.md` |
| `.claude/agents/core/reviewer.md` | `reviewer.md` |
| `.claude/agents/core/researcher.md` | `researcher.md` |
| `.claude/agents/core/planner.md` | `planner.md` |
| `.claude/agents/core/tester.md` | `tester.md` |
| `.claude/agents/security-auditor.md` | `security-auditor.md` |
| `.claude/agents/database-specialist.md` | `database-specialist.md` |
| `.claude/agents/typescript-specialist.md` | `typescript-specialist.md` |
| `.claude/agents/development/backend/dev-backend-api.md` | `backend-dev.md` |
| `.claude/agents/devops/ci-cd/ops-cicd-github.md` | `cicd-engineer.md` |
| `.claude/agents/testing/production-validator.md` | `production-validator.md` |
| `.claude/agents/testing/tdd-london-swarm.md` | `tdd-london.md` |

## Usage

- **As an agent-team teammate**: reference by `name:` frontmatter value when asking Claude to spawn a team, e.g. "Create a team with a `backend-dev` teammate on the Go API and a `typescript-specialist` teammate on the Next.js side."
- **As a one-shot subagent**: pass the `name` as `subagent_type` to the `Agent` tool.

Note that the `mcpServers` and `skills` frontmatter fields (if present) are not applied when a subagent definition runs as a teammate — teammates load skills and MCP servers from project/user settings like a regular session.

## Adding new agents

Keep one role per file. Prefer a tight description and a clear `tools` allowlist if you want to restrict the role. Don't pre-author anything under `~/.claude/teams/` or `.claude/teams/` — Claude Code owns those paths and overwrites hand edits.
