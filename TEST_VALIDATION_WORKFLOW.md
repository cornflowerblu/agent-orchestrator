# Test Validation Workflow

This document explains the test validation workflow implemented for the Agent Orchestrator platform.

## Overview

The project uses a **hybrid test validation strategy** that ensures code quality while enabling autonomous development:

1. **Enhanced Stop Hook** - Validates tests before every commit
2. **Ralph-Loop** - Enables autonomous TDD workflows for complex implementation phases
3. **Virtual Environment Automation** - Handles venv activation automatically

## Enhanced Stop Hook

### What It Does

The Stop hook runs automatically. It:

1. Checks for uncommitted changes
2. Activates the virtual environment
3. Runs pytest with coverage
4. Validates results against project requirements
5. Creates conventional commits if tests pass
6. Blocks commits if tests fail or coverage is insufficient

### Test Validation Rules

**PASS Criteria** (all must be true):

- Pytest exit code = 0 (all non-skipped tests passed)
- Coverage >= 80% (from pyproject.toml)
- No pytest execution errors

**FAIL Criteria** (any one triggers failure):

- Any test failure
- Coverage < 80%
- Pytest execution error

**Expected Behavior**:

- Integration tests marked with `@pytest.mark.integration` will be skipped (this is correct)
- Skipped integration tests do not cause failure

### What Tests Run

By default, the Stop hook runs:

```bash
pytest --cov=src --cov-report=term-missing -m "not integration"
```

This excludes integration tests because they require AWS deployment and are tested separately in CI/CD.

### Commit Creation

If tests pass, the Stop hook creates commits following **Constitution Principle VIII: Conventional Commits with Logical Chunks**.

The hook analyzes your changes and creates **multiple commits**, each representing a single logical unit:

- One commit per model/entity created
- One commit per service implemented
- One commit per test suite added
- Separate commits for config vs implementation

Example commits:

```
feat(consultation): add ConsultationPhase enum
feat(consultation): add ConsultationEngine class
test(consultation): add unit tests for consultation rules
```

### Failure Handling

If tests fail:

```
❌ Tests failed. Cannot commit.

[pytest failure output shown here]

Next steps:
1. Review failure output above
2. Fix failing tests or implementation
3. Re-run tests: source .venv/bin/activate && pytest -v
4. Try /stop again when tests pass
```

If coverage is below 80%:

```
❌ Coverage is 72% (required: 80%). Cannot commit.

Files below threshold:
- src/metadata/storage.py: 45% (missing lines: 23-45, 67-89)

Next steps:
1. Add tests for uncovered lines
2. Re-run: source .venv/bin/activate && pytest --cov=src
3. Try /stop again when coverage >= 80%
```

## Ralph-Loop for Autonomous Development

### What It Is

Ralph-loop is a self-correcting autonomous development loop that:

- Executes tasks from tasks.md using TDD workflow
- Runs tests after each change
- Fixes failures automatically
- Continues until completion criteria met

### When to Use

**Use ralph-loop for**:

- ✅ Complex implementation phases (US4, US5)
- ✅ Well-scoped feature development with clear tasks
- ✅ TDD workflows (write test → implement → validate → commit)

**Don't use ralph-loop for**:

- ❌ Ad-hoc changes or bug fixes
- ❌ Exploratory work
- ❌ Tasks requiring subjective judgment (code review, security audit)

### How to Use

For Phase 6 (Consultation Requirements):

```bash
/ralph-loop "/speckit.implement Phase 6 tasks (T050-T061)" --completion-promise "PHASE_US4_COMPLETE" --max-iterations 75
```

For Phase 7 (Registry API):

```bash
/ralph-loop "/speckit.implement Phase 7 tasks (T062-T083)" --completion-promise "PHASE_US5_COMPLETE" --max-iterations 100
```

### How It Works

1. Ralph-loop invokes `/speckit.implement`
2. `/speckit.implement` reads tasks.md and executes tasks using TDD
3. After each task, Stop hook runs tests
4. If tests pass: Continue to next task
5. If tests fail: Ralph-loop feeds prompt back, continues with fixes
6. When all tasks complete AND tests pass: Output completion promise
7. Ralph-loop detects promise and exits

### Completion Criteria

Ralph-loop ONLY exits when ALL criteria are met:

- ✅ All assigned tasks complete
- ✅ All tests pass
- ✅ Coverage meets target
- ✅ All changes committed
- ✅ Completion promise output

### Safety Limits

Each phase has a max-iterations limit:

- Phase 6: 75 iterations
- Phase 7: 100 iterations

If max iterations reached without completion, the agent outputs a progress summary for human review.

## Virtual Environment Automation

### Test Script

A helper script ensures consistent test execution:

```bash
.claude/scripts/test-with-venv.sh
```

This script:

1. Activates the virtual environment
2. Runs pytest with coverage
3. Excludes integration tests by default

### Usage

Run tests manually:

```bash
.claude/scripts/test-with-venv.sh -v
```

Run specific test markers:

```bash
.claude/scripts/test-with-venv.sh -m unit
```

Run with custom pytest options:

```bash
.claude/scripts/test-with-venv.sh --lf  # Run last failed tests
```

## Coverage Strategy

### Current Status

- **Current Coverage**: 50.34%
- **Target**: 80%
- **Gap**: 30 percentage points

### Phased Improvement

**Phase 6 (US4 - Consultation)** → Target: 60-65%

- Implement consultation module with comprehensive tests

**Phase 7 (US5 - Registry)** → Target: 75-80%

- Implement registry module with comprehensive tests
- **Backfill** missing coverage:
  - `src/metadata/storage.py`: 0% → 80%
  - `src/gateway/tools.py`: 40% → 80%

**Phase 8 (Polish)** → Target: 80%+

- Identify and test remaining gaps
- Ensure all modules meet threshold

### Coverage Reports

View coverage in terminal:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing
```

Generate HTML report:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=html
open htmlcov/index.html
```

Check specific module:

```bash
source .venv/bin/activate && pytest --cov=src/consultation --cov-report=term-missing
```

## Integration Tests

### Expected Behavior

Integration tests require AWS deployment and are marked with:

```python
@pytest.mark.integration
```

These tests are **expected to be skipped** in local development:

```
===== 35 passed, 5 skipped in 2.45s =====
```

This is correct behavior. Integration tests run in CI/CD with AWS credentials.

### Running Integration Tests

In local development (will skip):

```bash
source .venv/bin/activate && pytest -m integration
```

In CI/CD (with AWS credentials):

```bash
pytest  # Runs all tests including integration
```

## Constitutional Compliance

This workflow implements several Constitution principles:

### Principle III: Verification-First Completion

- Stop hook ensures tests pass before commits
- No code committed without validation

### Principle VI: Autonomous with Human Oversight

- Ralph-loop enables autonomous execution
- Max-iterations provides safety limit
- Human can intervene at any time

### Principle VIII: Conventional Commits with Logical Chunks

- Stop hook creates conventional commits automatically
- Each commit represents one logical unit
- Clear commit history for review

## Quick Reference

### Common Commands

Run all tests:

```bash
source .venv/bin/activate && pytest -v
```

Run with coverage:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing
```

Run only unit tests:

```bash
source .venv/bin/activate && pytest -m unit
```

Run specific test file:

```bash
source .venv/bin/activate && pytest tests/unit/test_consultation_rules.py -v
```

View coverage report:

```bash
open htmlcov/index.html  # After running pytest --cov-report=html
```

### Files

- `.claude/hooks/Stop/hook.md` - Enhanced Stop hook implementation
- `.claude/settings.local.json` - Hook configuration (120s timeout)
- `.claude/scripts/test-with-venv.sh` - Virtual environment test script
- `.claude/ralph-prompts/phase*.md` - Ralph-loop prompts for each phase
- `pyproject.toml` - Pytest and coverage configuration

## Troubleshooting

### "Virtual environment not found"

Create the virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### "Coverage below 80%"

Check which files need coverage:

```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing
```

Add tests for the files showing missing lines.

### "Tests failing"

Run tests with verbose output:

```bash
source .venv/bin/activate && pytest -v --tb=short
```

Fix the failing tests, then retry `/stop`.

### "Stop hook timing out"

The Stop hook has a 120s timeout. If tests take longer:

1. Check for slow tests (mark with `@pytest.mark.slow`)
2. Consider running only fast tests during development
3. Run full suite before final commits

## Next Steps

1. **Phase 6**: Use ralph-loop to implement consultation requirements (T050-T061)
2. **Phase 7**: Use ralph-loop to implement registry API (T062-T083)
3. **Phase 8**: Manual completion of polish and validation tasks (T084-T090)

## Additional Resources

- [Ralph-Loop Documentation](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Pytest Coverage Documentation](https://pytest-cov.readthedocs.io/)
- Project Constitution: `.specify/memory/constitution.md`
