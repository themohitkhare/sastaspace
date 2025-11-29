# SastaSpace Autonomous Agentic Team Architecture

## Executive Summary

This document describes the AI-powered agentic team architecture for SastaSpace, designed to augment a solo developer's workflow without becoming a maintenance burden. The system emphasizes pragmatic automation over theoretical perfection.

## Phase 1: Agent Personas & Responsibilities

### 1. Product Manager Agent (PM-Agent)

**Primary Goal**: Convert vague ideas into actionable GitHub Issues with clear acceptance criteria.

**System Prompt**: See `.cursorrules` for PM-Agent context.

**Workflow**:
1. User creates issue using GitHub Issue template
2. PM-Agent validates issue structure
3. Issue is labeled `status: todo` and `needs: architecture`

**Definition of Done**:
- ✅ Issue created in GitHub with all template sections filled
- ✅ Labeled correctly: `priority: [high/medium/low]`, `project: [frontend/backend/ai]`, `status: todo`
- ✅ Linked to relevant existing issues if dependencies exist
- ✅ Reviewed against existing codebase to avoid duplicate work

### 2. Software Architect Agent (Arch-Agent)

**Primary Goal**: Design scalable, Rails-idiomatic solutions before code is written.

**System Prompt**: See `.cursorrules` for Arch-Agent context.

**Workflow**:
1. Issue labeled `needs: architecture` triggers Arch-Agent
2. Arch-Agent analyzes requirements and existing codebase
3. Posts architecture comment on issue with:
   - Database schema changes (migrations)
   - Service objects for business logic
   - Controller structure (RESTful routes)
   - Background job orchestration
   - Caching strategy
   - Security considerations
4. Changes label to `ready: implementation`

**Definition of Done**:
- ✅ Architecture comment posted on issue within 2 hours
- ✅ All Rails conventions validated (no custom routing unless justified)
- ✅ Database indexes planned for new queries
- ✅ Security review completed (authorization, input validation)
- ✅ Label changed from `needs: architecture` to `ready: implementation`

### 3. Senior Engineer Agent (Review-Agent)

**Primary Goal**: Code review, standards enforcement, unblocking junior agents.

**System Prompt**: See `.cursorrules` for Review-Agent context.

**Workflow**:
1. PR created with label `ready: review`
2. Review-Agent runs automated checks (Rubocop, Brakeman, Tests)
3. Performs manual review:
   - Architecture alignment
   - Code smells
   - Missing edge cases
   - UX considerations
4. Posts review comments
5. Updates label: `ready: merge` (approved) or `needs: revision` (changes requested)

**Definition of Done**:
- ✅ PR reviewed within 4 hours of `ready: review` label
- ✅ All automated checks verified (CI, Rubocop, Brakeman)
- ✅ Inline comments on code quality issues
- ✅ Label updated: `ready: merge` (approved) or `needs: revision` (changes requested)

### 4. Software Engineer Agent (Code-Agent)

**Primary Goal**: Implement features according to Arch-Agent's design.

**System Prompt**: See `.cursorrules` for Code-Agent context.

**Workflow**:
1. Issue labeled `ready: implementation`
2. Create feature branch: `git checkout -b feature/issue-#{issue_number}-short-name`
3. TDD Cycle:
   - Write failing test
   - Implement minimal code to pass
   - Refactor
   - Verify no regressions
4. Run `bin/ci` locally
5. Create PR with proper description and labels

**Definition of Done**:
- ✅ All acceptance criteria from PM issue met
- ✅ Tests written first (TDD)
- ✅ Test coverage >80% for new code
- ✅ `bin/ci` passes (Rubocop + Brakeman + Tests)
- ✅ PR created with proper description and labels
- ✅ No new Bullet N+1 warnings

### 5. QA & Security Agent (QA-Agent)

**Primary Goal**: Automated testing pipeline + vulnerability scanning.

**System Prompt**: See `.cursorrules` for QA-Agent context.

**Workflow**:
1. PR labeled `ready: review` triggers QA-Agent
2. Runs full CI pipeline:
   - Rubocop
   - Brakeman
   - Tests (unit + system)
   - Coverage check
3. Posts QA report as PR comment
4. Updates label: `qa: approved`

**Definition of Done**:
- ✅ All CI checks green on PR
- ✅ Security scan passed (Brakeman 0 warnings)
- ✅ Test coverage maintained or improved
- ✅ QA report posted as PR comment
- ✅ Label updated: `qa: approved`

## Phase 2: Operational Workflow

### Sequential Flow: Feature Request → Deployment

```
User Story/Bug Report
    ↓
PM-Agent (Create GitHub Issue)
    ↓
Arch-Agent (Design Architecture)
    ↓
Code-Agent (Implement Feature)
    ↓
Review-Agent (Code Review)
    ↓
QA-Agent (Quality Assurance)
    ↓
Merge to Main
    ↓
Deploy via Kamal
```

### State Transitions (GitHub Labels)

| Label | Meaning | Next Action | Agent Responsible |
|-------|---------|-------------|-------------------|
| `status: todo` | Issue created, needs architecture | Assign Arch-Agent | PM-Agent |
| `needs: architecture` | Waiting for design | Create architecture comment | Arch-Agent |
| `ready: implementation` | Architecture approved | Assign Code-Agent | Human (you) or Auto |
| `status: in-progress` | Code being written | Create PR when done | Code-Agent |
| `ready: review` | PR open, needs review | Review code | Review-Agent |
| `needs: revision` | Changes requested | Fix issues, re-request review | Code-Agent |
| `qa: approved` | All checks passed | Merge PR | Human (you) |
| `status: done` | Merged and deployed | Close issue | Auto (GitHub) |

## Phase 3: Service Object Patterns

### Template: QuotaEnforcer Service

```ruby
# app/services/quota_enforcer.rb
class QuotaEnforcer
  class QuotaExceededError < StandardError; end

  LIMITS = {
    free: { inventory_items: 50, outfits: 10 },
    premium: { inventory_items: Float::INFINITY, outfits: Float::INFINITY }
  }.freeze

  def initialize(user)
    @user = user
  end

  def check!(resource_type)
    return true if @user.premium?

    current_count = @user.send(resource_type).count
    limit = LIMITS[@user.plan_type][resource_type]

    raise QuotaExceededError if current_count >= limit
    true
  end

  private

  attr_reader :user
end
```

### Template: Controller Action Using Service

```ruby
# app/controllers/inventory_items_controller.rb
def create
  QuotaEnforcer.new(current_user).check!(:inventory_items)

  @inventory_item = current_user.inventory_items.build(inventory_item_params)

  if @inventory_item.save
    redirect_to @inventory_item, notice: "Item added!"
  else
    render :new, status: :unprocessable_entity
  end
rescue QuotaEnforcer::QuotaExceededError
  redirect_to upgrade_path, alert: "Quota exceeded. Upgrade to Premium!"
end
```

### Template: Test for Service Object

```ruby
# test/services/quota_enforcer_test.rb
require "test_helper"

class QuotaEnforcerTest < ActiveSupport::TestCase
  setup do
    @user = users(:free_user)
    @enforcer = QuotaEnforcer.new(@user)
  end

  test "allows creation under quota" do
    assert @enforcer.check!(:inventory_items)
  end

  test "raises error when quota exceeded" do
    create_list(:inventory_item, 50, user: @user)

    assert_raises(QuotaEnforcer::QuotaExceededError) do
      @enforcer.check!(:inventory_items)
    end
  end

  test "allows unlimited for premium users" do
    @user.update!(plan_type: :premium)
    create_list(:inventory_item, 100, user: @user)

    assert @enforcer.check!(:inventory_items)
  end
end
```

## Phase 4: Tooling & Execution

### GitHub Integration

- **Issue Templates**: `.github/ISSUE_TEMPLATE/feature_request.yml`, `bug_report.yml`
- **Agent Orchestration**: `.github/workflows/agent_orchestration.yml`
- **Deployment**: `.github/workflows/deploy.yml`

### Cursor IDE Configuration

- **Rules File**: `.cursorrules` (contains all agent prompts and patterns)
- **Composer Prompts**: Use Cursor Composer with agent-specific prompts

### CI/CD Strategy

- **Pre-Deployment Checks**: `rails deploy:pre_check`
- **Post-Deployment Verification**: `rails deploy:post_check`
- **Full CI Suite**: Runs on every PR and before deployment

## Phase 5: Decision Matrix for Solo Developer

| Scenario | Human Decision | Agent Assists | Fully Automated |
|----------|---------------|---------------|-----------------|
| New Feature Idea | ✅ Define vision | PM-Agent writes issue | ❌ |
| Architecture Design | ✅ Review & approve | Arch-Agent proposes | ❌ |
| Writing Tests | ❌ | Code-Agent generates | ✅ (Cursor) |
| Implementation | ✅ Review AI code | Code-Agent writes | ❌ |
| Code Review | ✅ Final approval | Review-Agent checks | ❌ |
| Security Scan | ❌ | QA-Agent runs | ✅ (CI) |
| Merging PR | ✅ Manual merge | | ❌ |
| Deployment | ✅ Trigger manually | | ✅ (After merge) |
| Monitoring | ✅ Check logs | Alerts on errors | ✅ (Kamal health) |

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Issue→PR Time | <2 days | GitHub Analytics |
| PR→Merge Time | <4 hours | GitHub Analytics |
| Test Coverage | >85% | Simplecov |
| Security Issues | 0 critical | Brakeman |
| Deployment Frequency | 2x/week | Kamal logs |
| Agent Code Quality | Rubocop pass rate >95% | CI reports |

## Security Considerations

- **API Keys**: Store in GitHub Secrets (for Arch/Review agents calling LLMs)
- **Code Injection**: Agents never execute arbitrary code (only generate + review)
- **Human-in-the-Loop**: All merges require your approval
- **Audit Trail**: GitHub preserves all agent interactions as comments
- **Rate Limiting**: Protect Ollama endpoints from agent abuse

## Next Steps

1. Start with Issue #105 (Freemium Model) - it's well-defined and high priority
2. Set up PM-Agent first - creates foundation for all workflows
3. Use Cursor for Code-Agent - leverage existing IDE instead of building separate tool
4. Iterate quickly - adjust prompts based on first 3-5 issues

## References

- `.cursorrules` - Complete agent prompts and coding patterns
- `.github/workflows/agent_orchestration.yml` - Agent automation
- `.github/workflows/deploy.yml` - Deployment pipeline
- `lib/tasks/deploy.rake` - Pre/post deployment checks
