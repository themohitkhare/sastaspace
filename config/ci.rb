# Rails CI Configuration
# Local-first CI using Rails CI DSL
# Runs entirely on developer machines with no cloud dependency

CI.run do
  step "Setup", "bin/setup --skip-server"
  step "Style: Ruby", "bin/rubocop"

  step "Security: Gem audit", "bin/bundler-audit"
  step "Security: Importmap vulnerability audit", "bin/importmap audit"
  step "Security: Brakeman code analysis", "bin/brakeman --quiet --no-pager --exit-on-warn --exit-on-error"
  step "Tests: Rails", "COVERAGE=true bin/rails test"
  step "Tests: System", "bin/rails test:system"
  step "Tests: Seeds", "env RAILS_ENV=test bin/rails db:seed:replant"

  if success?
    step "Coverage: Summary", "echo 'Coverage report generated in coverage/ directory'"
    step "Signoff: All systems go. Ready for merge and deploy.", "echo 'Local CI passed'"
  else
    failure "Signoff: CI failed. Do not merge or deploy.", "echo 'Fix the issues and try again.'"
  end
end
