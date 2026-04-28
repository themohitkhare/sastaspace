#!/usr/bin/env bash
# Initialize a fresh sastaspace worktree for an autonomous Symphony-style run.
#
# Run from inside the freshly-cloned worktree. Builds the shell binary so the
# agent can exercise it during validation.
set -eo pipefail

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo is required. Install via https://rustup.rs" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required for PR operations. Install via https://cli.github.com" >&2
  exit 1
fi

# Pre-warm the build cache so first-run validation doesn't time out the agent.
cargo build -p shell

# Configure rerere so repeated merge conflicts auto-resolve cleanly.
git config rerere.enabled true
git config rerere.autoupdate true
