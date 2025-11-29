---
description: "Run all test suites (Unit, System, CI) and iteratively fix failures. Use this when acting as Code-Agent during development."
globs: []
---

# Run All Tests and Fix

Execute the full testing suite to ensure stability across environments.

> **Note**: This is used by Code-Agent during development. Always run `bin/ci` before creating a PR to ensure Review-Agent and QA-Agent checks will pass.

## 1. Run Tests

Execute the following commands in order. If any command fails, stop and fix the errors before proceeding.

### A. Standard Unit/Integration Tests
```bash
rails test
```

### B. System Tests (Headless)
```bash
rails test:system
```

### C. CI Pipeline Simulation
```bash
bin/ci
```
*(Note: `bin/ci` often includes linting and security checks which might catch issues that standard tests miss, or concurrency issues.)*

## 2. Fix Failures (Iterative Loop)

For each failure encountered:

1.  **Read Output**: Analyze the stack trace. Identify the specific file and line number of the failure.
2.  **Read Code**: Open the test file and the code under test.
3.  **Diagnose**:
    *   Is it a logic error?
    *   Is it a test setup issue (fixtures/factories)?
    *   Is it a "flaky" test (timing issue, often in system tests)?
    *   Is it a parallelization issue (happens in CI)?
4.  **Apply Fix**: Edit the code.
5.  **Verify**: Run *only* the failing test to verify the fix quickly.
    ```bash
    rails test <path/to/test.rb>:<line>
    ```
6.  **Regression**: Once fixed, run the full suite step again.

## Common Issues in SastaSpace

*   **Ollama/AI**: Ensure network calls are stubbed/mocked. Real AI calls should not happen in tests.
*   **Hardcoded IDs**: Look for hardcoded IDs causing collisions in parallel tests.
*   **Database State**: Ensure proper teardown if using non-transactional tests (System tests).

