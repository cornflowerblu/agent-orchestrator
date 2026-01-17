# Stop Hook: Test Validation Before Commit

Check for uncommitted changes and validate tests before creating commits.

## Workflow

### Step 1: Check for Uncommitted Changes

Run `git status --porcelain` to check for uncommitted changes.

- If no changes exist: Exit (nothing to commit)
- If changes exist: Proceed to Step 2

### Step 2: Run Test Validation

Execute the following command to run tests with coverage:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration and not sam_local"
```

**Important Notes**:
- Virtual environment MUST be activated before running pytest
- The `-m "not integration and not sam_local"` flag excludes:
  - `integration` tests (require AWS deployment)
  - `sam_local` tests (require LocalStack + Docker, run in CI parallel job)
- Coverage report shows missing lines for any files below threshold

**Expected Behavior**:
- Integration tests marked with `@pytest.mark.integration` will be skipped (this is expected and correct)
- Pytest exit code 0 with skipped tests = PASS
- Coverage is calculated only on tested code (integration tests excluded)

### Step 3: Evaluate Test Results

Check the pytest exit code and coverage percentage:

**PASS Criteria** (All must be true):
- Pytest exit code = 0 (all non-skipped tests passed)
- Coverage >= 80% (from pyproject.toml fail_under setting)
- No pytest execution errors

**FAIL Criteria** (Any one triggers failure):
- Any test failure (pytest exit code != 0)
- Coverage < 80%
- Pytest execution error

### Step 4a: If Tests PASS - Create Commits

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

### Step 4b: If Tests FAIL - Block Commit

**DO NOT create any commits.**

Display clear failure information:

```
❌ Tests failed. Cannot commit.

[Show pytest failure output or coverage report]

Next steps:
1. Review failure output above
2. Fix failing tests or add missing test coverage
3. Re-run tests: source .venv/bin/activate && pytest -v
4. Try /stop again when tests pass
```

**If Tests Failed**:
- Show which tests failed and why
- Show full pytest output for debugging

**If Coverage Below 80%**:
- Show coverage report with missing lines
- Identify files below threshold
- Suggest specific lines that need test coverage

## Safety Rules

1. **Never skip test validation** - Tests MUST run on every stop if changes exist
2. **Never create commits if tests fail** - Zero exceptions
3. **Never create commits if coverage < 80%** - Constitutional requirement
4. **Always activate virtual environment** - Tests will fail otherwise
5. **Always create logical chunks** - Follow Constitution Principle VIII

## Edge Cases

### Skipped Integration Tests
- Integration tests are EXPECTED to be skipped (require AWS deployment)
- Pytest exit code 0 with skipped tests = PASS
- Only fail if non-integration tests fail

### Virtual Environment Missing
If `.venv/bin/activate` does not exist:
```
❌ Virtual environment not found at .venv

To fix:
1. Create venv: python3 -m venv .venv
2. Install dependencies: .venv/bin/pip install -e ".[dev]"
3. Try /stop again
```

### No Test Files
If no tests exist yet (early project stage):
- Warn that no tests exist
- Still allow commit (with warning)
- Remind to add tests following TDD workflow

## Constitutional Compliance

This hook implements:
- ✅ **Principle III (Verification-First Completion)**: Tests must pass before commit
- ✅ **Principle VIII (Conventional Commits with Logical Chunks)**: Enforces conventional commit format and logical chunking
- ✅ **Constitution requirement**: 80% coverage threshold from pyproject.toml

## Success Output

When validation passes and commits created:

```
✅ All tests passed (X/X tests, Y skipped)
✅ Coverage: Z.Z% (threshold: 80%)

Created commits:
1. feat(module): description
2. test(module): description
3. ...

Status: Ready for push
```
