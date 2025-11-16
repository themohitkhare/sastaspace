# Rails CI Configuration
# Local-first CI using Rails CI DSL
# Runs entirely on developer machines with no cloud dependency
# Aligned with SAS-21: RuboCop, Brakeman, Bundler Audit, Minitest with SimpleCov

CI.run do
  step "Style: Ruby", "bundle exec rubocop -A"
  step "Security: Brakeman", "bundle exec brakeman -q -w2"
  step "Security: Bundler Audit", "bundle exec bundle-audit check --update"
  # Run all tests including system tests with coverage
  # System tests use Cuprite (headless Chrome) which should be available
  step "Tests: Rails with Coverage", "SIMPLECOV=1 rails test:full"
  step "Tests: System", "SIMPLECOV=1 rails test:system:full"

  if success?
    step "Coverage: Summary", "echo 'Coverage report generated in coverage/ directory' && if [ -f coverage/.last_run.json ]; then echo 'Coverage data available. View coverage/index.html for details.'; fi"
    step "Signoff: All systems go. Ready for merge and deploy.", "echo 'Local CI passed'"
  else
    failure "Signoff: CI failed. Do not merge or deploy.", "echo 'Fix the issues and try again.'"
  end
end
