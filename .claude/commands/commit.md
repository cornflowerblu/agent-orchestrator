---
description: Validate tests and create conventional commits with logical chunks
---

# Commit Skill - Test Validation and Conventional Commits

Validates tests pass and coverage meets threshold before creating commits. Follows Constitution Principle III (Verification-First) and Principle VIII (Conventional Commits).

## Step 1: Check for Uncommitted Changes

Run `git status --porcelain` to check for uncommitted changes.

- If no changes exist: Report "Nothing to commit" and exit
- If changes exist: Proceed to Step 2

## Step 2: Run Unit Test Validation

Execute the following command to run unit tests with coverage:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration and not sam_local"
```

**Notes**:
- Virtual environment MUST be activated before running pytest
- The `-m "not integration and not sam_local"` flag excludes:
  - `integration` tests (require real AWS deployment)
  - `sam_local` tests (require LocalStack + Docker, run in CI parallel job)
- Pytest exit code 0 = PASS

## Step 3: Evaluate Unit Test Results

**PASS Criteria** (All must be true):
- Pytest exit code = 0 (all non-skipped tests passed)
- Coverage >= 80% (from pyproject.toml fail_under setting)
- No pytest execution errors

**FAIL Criteria** (Any one triggers failure):
- Any test failure (pytest exit code != 0)
- Coverage < 80%
- Pytest execution error

**If unit tests FAIL**: Skip to Step 4b (Block Commit)
**If unit tests PASS**: Proceed to Step 3a (Integration Tests)

## Step 3a: Run Local Integration Test Validation

After unit tests pass, execute local integration tests:

```bash
source .venv/bin/activate && pytest -m integration_local -v
```

**Notes**:
- Only run if Step 2 (unit tests) passed
- Virtual environment MUST be activated before running pytest
- The `-m integration_local` flag runs only local integration tests
- **No coverage requirement** - these tests just need to pass
- Coverage is measured in CI/CD with E2E integration tests (60% threshold)
- These tests do NOT require AWS deployment

## Step 3b: Evaluate Integration Test Results

**PASS Criteria**:
- Pytest exit code = 0 (all tests passed)
- No pytest execution errors

**FAIL Criteria**:
- Any test failure (pytest exit code != 0)
- Pytest execution error

**Output Format When PASS**:
```
✅ Unit tests: X passed, Y.YY% coverage (threshold: 80%)
✅ Local integration tests: X passed
```

**Output Format When FAIL**:
```
✅ Unit tests: X passed, Y.YY% coverage (threshold: 80%)
❌ Local integration tests failed

[Show pytest failure output]
```

**If integration tests FAIL**: Skip to Step 4b (Block Commit)
**If integration tests PASS**: Proceed to Step 4a (Create Commits)

## Step 4a: If Tests PASS - Create Commits

Follow **Constitution Principle VIII: Conventional Commits with Logical Chunks**

**Commit Message Format**:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Required Types**:
- `feat:` - New feature or capability
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Formatting, whitespace (no code change)
- `refactor:` - Code restructuring (no feature/fix)
- `test:` - Adding or updating tests
- `chore:` - Build, config, tooling changes

**Logical Chunk Rules**:

Analyze the uncommitted changes and create MULTIPLE commits, each representing a single logical unit of work:

- One commit per model/entity created
- One commit per service implemented
- One commit per API endpoint added
- One commit per test suite added
- Separate commits for config vs implementation
- Never batch unrelated changes into a single commit

**Examples of Good Logical Chunks**:
```
feat(consultation): add ConsultationPhase enum
feat(consultation): add ConsultationCondition model
feat(consultation): add ConsultationEngine class
test(consultation): add unit tests for consultation rules
```

**Commit Process**:
1. Stage files for the first logical chunk: `git add <files>`
2. Create commit with conventional format
3. Repeat for each logical chunk until all changes committed
4. Display summary of commits created

## Step 4b: If Tests FAIL - Block Commit

**DO NOT create any commits.**

Display clear failure information based on which step failed:

**If Unit Tests Failed (Step 2)**:
```
❌ Unit tests failed. Cannot commit.

[Show pytest failure output or coverage report]

Next steps:
1. Review failure output above
2. Fix failing tests or add missing test coverage
3. Re-run tests: source .venv/bin/activate && pytest -v
4. Try /commit again when tests pass
```

**If Integration Tests Failed (Step 3a)**:
```
✅ Unit tests: X passed, Y.YY% coverage (threshold: 80%)
❌ Local integration tests failed

[Show pytest failure output]

Next steps:
1. Review failure output above
2. Fix failing tests
3. Re-run tests: source .venv/bin/activate && pytest -m integration_local -v
4. Try /commit again when tests pass
```

**For Unit Test Failures**:
- Show which tests failed and why
- Show full pytest output for debugging
- If coverage < 80%: Show coverage report with missing lines

**For Integration Test Failures**:
- Show which integration tests failed and why
- Show full pytest output for debugging
- No coverage requirement (tests just need to pass)

## Edge Cases

### No Integration Tests Yet
If no integration tests exist yet (early project stage):
- Integration test step will show "no tests ran"
- This is ALLOWED - proceed to commit
- Remind user to add integration tests following TDD workflow

### Virtual Environment Missing
If `.venv/bin/activate` does not exist:
```
❌ Virtual environment not found at .venv

To fix:
1. Create venv: python3 -m venv .venv
2. Install dependencies: .venv/bin/pip install -e ".[dev]"
3. Try /commit again
```

### No Test Files
If no tests exist yet (early project stage):
- Warn that no tests exist
- Still allow commit (with warning)
- Remind to add tests following TDD workflow

## Success Output

When validation passes and commits created:

```
✅ Unit tests: X passed, Y.YY% coverage (threshold: 80%)
✅ Local integration tests: X passed

Created commits:
1. feat(module): description
2. test(module): description
3. ...

Status: Ready for push
```

## Constitutional Compliance

This skill implements:
- ✅ **Principle III (Verification-First Completion)**: Tests must pass before commit
- ✅ **Principle VIII (Conventional Commits with Logical Chunks)**: Enforces conventional commit format and logical chunking
