# Agentic Team Quick Reference

## 🚀 Getting Started

### For New Features

1. **Create Issue** → Use `.github/ISSUE_TEMPLATE/feature_request.yml`
2. **PM-Agent** → Validates issue structure (auto)
3. **Add Label** → `needs: architecture`
4. **Arch-Agent** → Designs solution (auto or manual)
5. **Change Label** → `ready: implementation`
6. **Code-Agent** → Implements feature (you + Cursor)
7. **Create PR** → Label `ready: review`
8. **Review-Agent** → Reviews code (auto checks + manual)
9. **QA-Agent** → Runs full CI suite (auto)
10. **Merge** → When `qa: approved`

### For Bugs

1. **Create Issue** → Use `.github/ISSUE_TEMPLATE/bug_report.yml`
2. **Label** → `type: bug`, `priority: [P0-P3]`
3. **Fix** → Create PR with fix
4. **Review** → Same as feature workflow

## 📋 Label Reference

| Label | When to Use | Next Step |
|-------|-------------|-----------|
| `status: todo` | New issue created | Add `needs: architecture` |
| `needs: architecture` | Issue needs design | Wait for Arch-Agent or design manually |
| `ready: implementation` | Architecture approved | Start coding |
| `status: in-progress` | Currently coding | Create PR when done |
| `ready: review` | PR ready for review | Wait for Review-Agent |
| `needs: revision` | Changes requested | Fix and re-request review |
| `qa: approved` | All checks passed | Merge PR |
| `status: done` | Merged and deployed | Close issue |

## 🛠️ Common Commands

### Development
```bash
# Run full CI locally
bin/ci

# Run tests only
bin/rails test

# Run with coverage
COVERAGE=1 bin/rails test

# Check code style
bin/rubocop --autocorrect-all

# Security scan
bin/brakeman --quiet
```

### Deployment
```bash
# Pre-deployment checks
bin/rails deploy:pre_check

# Post-deployment verification
bin/rails deploy:post_check

# Full check (pre + post)
bin/rails deploy:check
```

### Database
```bash
# Check migration status
bin/rails db:migrate:status

# Run migrations
bin/rails db:migrate

# Rollback
bin/rails db:rollback
```

## 🎯 Agent Prompts for Cursor

### Acting as Code-Agent
```
Act as Code-Agent implementing [Issue #X]. 
Read the architecture comment on the issue and implement exactly as designed.
Use TDD: write failing tests first, then implement minimal code to pass.
Run bin/ci before committing.
```

### Acting as Review-Agent
```
Act as Review-Agent reviewing this PR.
Check for:
1. Rails conventions followed?
2. N+1 queries possible?
3. Security issues (authorization, input validation)?
4. Test coverage adequate?
5. Architecture alignment?
```

### Acting as Arch-Agent
```
Act as Arch-Agent designing solution for [Issue #X].
Design:
1. Database schema changes (migrations)
2. Service objects needed
3. Controller actions (RESTful)
4. Background jobs if needed
5. Security considerations
Post as architecture comment on issue.
```

## 📁 File Locations

- **Issue Templates**: `.github/ISSUE_TEMPLATE/`
- **Workflows**: `.github/workflows/`
- **Cursor Rules**: `.cursorrules`
- **Deploy Tasks**: `lib/tasks/deploy.rake`
- **Documentation**: `docs/`

## 🔍 Troubleshooting

### Issue not triggering agents?
- Check labels are correct
- Verify workflow file exists: `.github/workflows/agent_orchestration.yml`
- Check GitHub Actions tab for workflow runs

### Pre-deployment checks failing?
- Run locally: `bin/rails deploy:pre_check`
- Check environment variables are set
- Verify database/Redis connections

### CI failing?
- Run locally: `bin/ci`
- Check Rubocop: `bin/rubocop`
- Check Brakeman: `bin/brakeman`
- Run tests: `bin/rails test`

## 📚 Full Documentation

See `docs/AGENT_ARCHITECTURE.md` for complete architecture documentation.
