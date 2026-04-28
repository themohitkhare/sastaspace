---
name: linear
description:
  Interact with Linear via the configured `plugin:linear:linear` MCP server;
  use for reading issues, transitioning state, posting/updating comments,
  attaching PRs, and similar tracker operations during workflow execution.
---

# Linear

Use this skill for all Linear operations. The MCP server `plugin:linear:linear`
exposes high-level tools for the common tracker operations Symphony's WORKFLOW
needs — there is no need to write raw GraphQL.

## Tool inventory

The Linear MCP tools are namespaced `mcp__plugin_linear_linear__*`. The ones
you will use most:

| Operation | Tool |
|---|---|
| List teams | `list_teams` |
| List issues for a team/project | `list_issues` |
| Get one issue by identifier or id | `get_issue` |
| Create or update an issue | `save_issue` |
| List comments on an issue | `list_comments` |
| Create or update a comment | `save_comment` |
| Delete a comment | `delete_comment` |
| List workflow states for a team | `list_issue_statuses` |
| Get one state by name or id | `get_issue_status` |
| List projects | `list_projects` |
| Create or update a project | `save_project` |
| Create an issue label | `create_issue_label` |
| List issue labels | `list_issue_labels` |
| Attach a URL to an issue | `create_attachment` |
| List milestones | `list_milestones` |
| Save a milestone | `save_milestone` |

These tools accept Linear identifiers (UUIDs) **or** human-friendly values
(team name, issue identifier like `SAS-32`, state name like `In Progress`).
Pass the friendly value when you have it; the server resolves it.

## Common workflows

### Read an issue by identifier

Call `get_issue` with `{ "query": "SAS-32" }` (or pass an internal UUID). It
returns the canonical issue record including `state.name`, `state.id`,
`project`, `branchName`, `url`, `description`, etc.

### Move an issue to a different state

1. If you do not yet know the destination state's id, call
   `list_issue_statuses` with `{ "team": "Sastaspace" }` and pick the row
   whose `name` matches your target.
2. Call `save_issue` with `{ "id": "<issue-id-or-identifier>", "state": "<state-id-or-name>" }`.

State names you should expect for the Sastaspace team:
`Backlog`, `Todo`, `In Progress`, `In Review`, `Rework`, `Merging`, `Done`,
`Canceled`, `Duplicate`.

### Find or create the workpad comment

1. Call `list_comments` with `{ "issue": "<identifier>" }`.
2. Scan returned comments for a body that begins with `## Agent Workpad`. If
   found, reuse its `id`.
3. If not found, call `save_comment` with
   `{ "issueId": "<issue-id>", "body": "<workpad markdown>" }` and persist
   the returned `id`.
4. To update the workpad later, call `save_comment` with
   `{ "id": "<comment-id>", "body": "<full updated markdown>" }`. Always
   write the full new body — there is no patch operation.

### Attach a PR URL to an issue

Call `create_attachment` with
`{ "issueId": "<issue-id>", "url": "<pr-url>", "title": "<pr-title>" }`.
Linear renders GitHub PRs natively and unfurls metadata automatically.

### Create a follow-up issue for out-of-scope work

Call `save_issue` with at least:

```json
{
  "team": "Sastaspace",
  "project": "Sastaspace",
  "title": "<concise title>",
  "description": "<acceptance criteria + context>",
  "state": "Backlog",
  "labels": ["<area-label>"],
  "relations": [
    { "issueId": "<current-issue-id>", "type": "related" }
  ]
}
```

If the follow-up depends on the current issue, use `type: "blocked_by"` (the
exact relation key may need a quick check via `list_issues` shape — the
server validates).

### Discover unfamiliar fields

When a tool's input shape is unclear, prefer reading the tool's schema via
`ToolSearch` (it shows the JSONSchema definition for each MCP tool) over
guessing. Do not fall back to raw GraphQL.

## Usage rules

- Use the `plugin:linear:linear` MCP tools for all Linear operations. Do not
  shell out to `curl` or write raw GraphQL.
- Pass strings as real strings (Linear MCP server expects literal newlines in
  markdown content, not `\n` escape sequences).
- Prefer the narrowest issue lookup that matches what you already know:
  identifier (`SAS-32`) -> internal id.
- For state transitions, pass the state name (`"In Progress"`) and let the
  server resolve it; or look up the id via `list_issue_statuses` if you need
  determinism.
- Keep the workpad in a single comment — never create a second `## Agent
  Workpad` comment on the same issue.
- When creating follow-up issues, always set `state: "Backlog"`,
  `project: "Sastaspace"`, and link the parent via `relations`.
