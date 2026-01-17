---
description: Autonomous git push with CI/CD pipeline monitoring and self-healing - keeps iterating until pipeline passes
---

## Ralph Push - Autonomous Pipeline Troubleshooting

This skill implements a self-correcting deployment loop that:
1. Pushes code to git remote
2. Monitors the CI/CD pipeline in real-time
3. Analyzes failures and fixes them autonomously
4. Continues iterating until ALL pipeline checks pass
5. Respects max-iterations safety limit

## User Input

```text
$ARGUMENTS
```

## Parsing Arguments

Parse the user input to extract:
- **branch**: Branch to push (default: current branch)
- **remote**: Remote to push to (default: origin)
- **max-iterations**: Maximum fix iterations before stopping (default: 5)
- **force**: Whether to force push (default: false)

Example: `/ralph-push` (uses current branch)
Example: `/ralph-push --branch main --max-iterations 10`
Example: `/ralph-push --remote upstream`

## Loop Execution

### Initialize Loop State

```
ITERATION = 0
MAX_ITERATIONS = [parsed max-iterations or 5]
CURRENT_BRANCH = [parsed branch or current branch]
REMOTE = [parsed remote or "origin"]
LOOP_ACTIVE = true
PIPELINE_PASSING = false
```

### Main Loop

**While LOOP_ACTIVE and ITERATION < MAX_ITERATIONS:**

1. **Increment iteration**: `ITERATION += 1`

2. **Display iteration header**:
   ```
   ════════════════════════════════════════════════════════
   RALPH PUSH - Iteration {ITERATION}/{MAX_ITERATIONS}
   ════════════════════════════════════════════════════════
   Branch: {CURRENT_BRANCH}
   Remote: {REMOTE}
   ```

3. **Push to remote**:
   ```bash
   git push {REMOTE} {CURRENT_BRANCH}
   ```

   - Pre-push hook will run automatically (lint, format, type check)
   - If pre-push hook fails: Fix issues locally and retry push
   - If push succeeds: Proceed to pipeline monitoring

4. **Get latest workflow run**:
   ```bash
   gh run list --branch {CURRENT_BRANCH} --limit 1 --json databaseId,status,conclusion,url
   ```

   Parse the response to get:
   - `RUN_ID`: The workflow run ID
   - `RUN_URL`: The GitHub Actions URL

5. **Display pipeline monitoring**:
   ```
   ────────────────────────────────────────────────────────
   Monitoring Pipeline Run: {RUN_ID}
   URL: {RUN_URL}
   ────────────────────────────────────────────────────────
   ```

6. **Stream pipeline logs** (watch for failures):
   ```bash
   gh run watch {RUN_ID} --exit-status
   ```

   This will:
   - Show real-time progress of all jobs
   - Exit with status 0 if all jobs pass
   - Exit with status 1 if any job fails

7. **Check pipeline result**:

   **If pipeline PASSES (exit status 0)**:
   - Set `PIPELINE_PASSING = true`
   - Set `LOOP_ACTIVE = false`
   - Display success message
   - EXIT LOOP

   **If pipeline FAILS (exit status 1)**:
   - Fetch failed job logs
   - Analyze the failure
   - Determine fix strategy
   - Apply fixes
   - Continue to next iteration

8. **Analyze pipeline failure** (if pipeline failed):

   a. **Fetch failed job logs**:
   ```bash
   gh run view {RUN_ID} --log-failed
   ```

   b. **Parse the logs** to identify:
   - Which job(s) failed (lint, test, type-check, cdk-synth, security, etc.)
   - Specific error messages
   - Files involved
   - Root cause

   c. **Categorize the failure**:
   - **Linting errors**: ruff check failures
   - **Formatting errors**: ruff format failures
   - **Type errors**: mypy failures
   - **Test failures**: pytest failures
   - **Coverage failures**: coverage < 80%
   - **CDK synth errors**: infrastructure issues
   - **Security issues**: bandit or pip-audit failures
   - **Build errors**: dependency or config issues

9. **Fix the failure** (based on category):

   **For linting errors**:
   - Run `ruff check --fix .` locally
   - Review and commit fixes

   **For formatting errors**:
   - Run `ruff format .` locally
   - Commit formatting changes

   **For type errors**:
   - Analyze mypy errors
   - Add type annotations or casts
   - Verify with `mypy src/`
   - Commit type fixes

   **For test failures**:
   - Analyze failing tests
   - Fix the underlying bug
   - Verify tests pass locally
   - Commit bug fix

   **For coverage failures**:
   - Identify uncovered code
   - Write missing tests
   - Verify coverage >= 80%
   - Commit new tests

   **For CDK synth errors**:
   - Analyze CDK error messages
   - Fix infrastructure code
   - Test with `cdk synth` locally
   - Commit infrastructure fix

   **For security issues**:
   - Review security vulnerability
   - Update dependencies or fix code
   - Commit security fix

   **For build errors**:
   - Fix dependency issues
   - Update pyproject.toml or requirements
   - Commit build fix

10. **Commit the fix**:
    - Use the `/commit` skill to create logical commits
    - This ensures tests pass before committing
    - Follows Constitution Principle VIII (Conventional Commits)

11. **Display iteration summary**:
    ```
    ────────────────────────────────────────────────────────
    Iteration {ITERATION} Summary
    ────────────────────────────────────────────────────────
    Pipeline Status: FAILED
    Failed Job: [job name]
    Error Type: [category]
    Fix Applied: [description]
    Status: PUSHING FIX (next iteration)
    ────────────────────────────────────────────────────────
    ```

12. **Loop continues** to push the fix and monitor again

### Exit Conditions

The loop exits when ANY of these conditions are met:

1. **Pipeline Passes** (SUCCESS):
   - All CI/CD jobs pass
   - Green checkmarks across the board
   - Output: Success message with run URL

2. **Max Iterations Reached** (SAFETY EXIT):
   - Display failure summary
   - Show what was attempted
   - Provide manual intervention steps
   - Link to failed run

3. **Unrecoverable Error** (MANUAL INTERVENTION REQUIRED):
   - Error that can't be fixed autonomously
   - Requires human decision-making
   - Display error details and guidance

### Final Output

**On Success:**
```
════════════════════════════════════════════════════════
RALPH PUSH COMPLETE - PIPELINE PASSING ✅
════════════════════════════════════════════════════════
Total iterations: {ITERATION}
All pipeline checks: PASSED

Pipeline URL: {RUN_URL}

Jobs passed:
✅ Lint
✅ Test (Coverage: XX.X%)
✅ Type Check
✅ Security Scan
✅ CDK Synth

Your code is deployed and all quality gates passed!
════════════════════════════════════════════════════════
```

**On Max Iterations:**
```
════════════════════════════════════════════════════════
RALPH PUSH - MAX ITERATIONS REACHED
════════════════════════════════════════════════════════
Total iterations: {MAX_ITERATIONS}
Pipeline Status: STILL FAILING

Latest failure:
Job: [job name]
Error: [error message]

Attempted fixes:
{ITERATION} 1: [description]
{ITERATION} 2: [description]
...

Pipeline URL: {RUN_URL}

Next steps:
1. Review the pipeline logs manually: {RUN_URL}
2. The issue may require human judgment
3. Fix locally and try /ralph-push again
════════════════════════════════════════════════════════
```

**On Unrecoverable Error:**
```
════════════════════════════════════════════════════════
RALPH PUSH - MANUAL INTERVENTION REQUIRED
════════════════════════════════════════════════════════
Error Type: [category]
Error Message: [details]

This error requires human decision-making:
- [Specific reason why it's unrecoverable]

Pipeline URL: {RUN_URL}

Suggested actions:
1. [Action 1]
2. [Action 2]
════════════════════════════════════════════════════════
```

## Pre-Push Hook Integration

The pre-push hook (`.git/hooks/pre-push`) runs automatically before each push:
- Linting check (ruff check)
- Formatting check (ruff format --check)
- Type checking (mypy src/)

If the hook fails, fix issues locally before the push succeeds.

## Pipeline Job Monitoring

The skill monitors these CI/CD jobs:

1. **Lint** - Ruff linting check
2. **Test** - Pytest with 80% coverage requirement
3. **Type Check** - Mypy static type analysis
4. **Security** - Bandit and pip-audit scans
5. **CDK Synth** - Infrastructure validation

Each job must pass for the pipeline to be considered successful.

## Common Failure Patterns

### CDK Synth Failures
- Virtual environment path issues → Fix cdk.json
- Missing dependencies → Update pyproject.toml
- AWS credential issues → Check OIDC setup
- CloudFormation errors → Fix stack code

### Test Coverage Failures
- Add tests for uncovered code
- Target: 80% minimum coverage
- Focus on critical paths

### Type Check Failures
- Add missing type annotations
- Use `cast()` for dynamic types
- Fix incorrect type signatures

## Constitutional Compliance

This skill implements:
- **Principle III (Verification-First)**: Pipeline must pass before declaring success
- **Principle VI (Autonomous with Oversight)**: Max-iterations safety limit
- **Principle VIII (Conventional Commits)**: Fixes committed as logical chunks

## Example Usage

```bash
# Push current branch and auto-fix pipeline failures
/ralph-push

# Push to main with higher iteration limit
/ralph-push --branch main --max-iterations 10

# Push to upstream remote
/ralph-push --remote upstream

# Push with custom branch
/ralph-push --branch feature/new-agent
```
