# Phase 8: Polish & Validation - Manual Completion Reference

**Strategy**: Manual completion with Enhanced Stop Hook (NOT ralph-loop)

**Rationale**: These are cross-cutting tasks requiring human judgment, subjective assessment, and manual verification. They don't fit the autonomous TDD loop pattern.

## Context

Phase 8 addresses quality, security, and operational concerns that span multiple user stories. These tasks require careful human review rather than autonomous execution.

## Tasks (7 Total)

- [ ] T084 [P] Create GitHub Actions CI workflow in .github/workflows/ci.yml
- [ ] T085 [P] Add test coverage configuration with 80% minimum threshold
- [ ] T086 [P] Create integration test stack naming and cleanup in infrastructure/cdk/
- [ ] T087 Run quickstart.md validation to verify all examples work
- [ ] T088 Code cleanup and ensure consistent error handling across modules
- [ ] T089 Security review of DynamoDB access patterns and IAM roles
- [ ] T090 Performance validation: Agent Card discovery < 500ms for 100 agents

## Task Breakdown

### T084: GitHub Actions CI Workflow

**Purpose**: Automate test validation on every PR and push

**Approach**:
1. Create `.github/workflows/ci.yml`
2. Define jobs:
   - Checkout code
   - Set up Python 3.11
   - Install dependencies
   - Run pytest with coverage
   - Fail if tests fail or coverage < 80%
3. Configure triggers: push to main, all PRs
4. Add status badge to README.md

**Manual Validation**:
- Push to branch and verify workflow runs
- Check that failing tests block PR merge
- Verify coverage reports are generated

**Commit**:
```
chore(ci): add GitHub Actions workflow for automated testing

- Run pytest on all pushes and PRs
- Enforce 80% coverage requirement
- Block merge if tests fail
```

---

### T085: Test Coverage Configuration

**Purpose**: Ensure coverage tracking is comprehensive and accurate

**Approach**:
1. Review `pyproject.toml` coverage settings
2. Add coverage exclusions if needed (`# pragma: no cover`)
3. Configure coverage reports (HTML, XML for CI)
4. Set per-module coverage targets if needed
5. Document coverage expectations in README.md

**Manual Validation**:
- Run coverage locally: `pytest --cov=src --cov-report=html`
- Open `htmlcov/index.html` and review each module
- Verify no critical code is excluded improperly

**Commit**:
```
chore(test): refine coverage configuration and exclusions

- Add coverage exclusions for unreachable code
- Configure HTML and XML coverage reports
- Document coverage requirements in README
```

---

### T086: Integration Test Stack Naming and Cleanup

**Purpose**: Enable integration tests to run in AWS without conflicts

**Approach**:
1. Add stack naming with unique suffixes (e.g., timestamp, branch name)
2. Create cleanup script to delete test stacks
3. Add integration test fixtures that deploy/teardown stacks
4. Document how to run integration tests locally

**Manual Validation**:
- Deploy test stack to AWS
- Run integration tests
- Verify cleanup removes all resources
- Check no orphaned resources remain

**Commit**:
```
chore(infra): add integration test stack naming and cleanup

- Use unique suffixes for test stacks
- Add cleanup script for test resources
- Document integration test execution
```

---

### T087: Quickstart Validation

**Purpose**: Ensure all documentation examples work as written

**Approach**:
1. Read `quickstart.md` (or create if missing)
2. Follow every example step-by-step
3. Verify commands execute without errors
4. Verify expected outputs match documentation
5. Update documentation for any discrepancies

**Manual Validation**:
- Fresh clone of repository
- Follow quickstart from scratch
- Note any issues or unclear steps
- Test on clean environment

**Commit**:
```
docs(quickstart): validate and update quickstart examples

- Verified all examples execute correctly
- Updated commands for current project structure
- Added clarifications for setup steps
```

---

### T088: Code Cleanup and Error Handling

**Purpose**: Ensure consistent quality and error handling patterns

**Approach**:
1. Review all modules for inconsistent error handling
2. Ensure all errors are logged properly
3. Add error context (what failed, why, how to fix)
4. Check for TODO/FIXME comments and address them
5. Verify consistent naming conventions
6. Remove dead code or commented-out code

**Manual Review Areas**:
- `src/metadata/storage.py` - DynamoDB error handling
- `src/gateway/tools.py` - MCP client error handling
- `src/consultation/enforcement.py` - Consultation validation errors
- `src/registry/handlers.py` - Lambda handler error responses

**Commit Pattern** (multiple commits):
```
refactor(metadata): improve error handling in storage layer
refactor(gateway): add error context to tool invocation failures
style: remove dead code and address TODO comments
```

---

### T089: Security Review

**Purpose**: Ensure no security vulnerabilities in AWS access patterns

**Approach**:
1. **DynamoDB Access**:
   - Review IAM policies for least privilege
   - Check that table policies don't allow overly broad access
   - Verify encryption at rest is enabled
   - Check that sensitive data is not logged

2. **Lambda Functions**:
   - Review Lambda execution role permissions
   - Ensure no hardcoded credentials
   - Verify environment variables are encrypted
   - Check that Lambda functions validate all inputs

3. **API Gateway**:
   - Verify authentication is enabled (if required)
   - Check for input validation on all endpoints
   - Ensure no sensitive data in URLs or logs
   - Review CORS configuration

4. **General**:
   - Check for any hardcoded AWS account IDs
   - Verify no secrets in version control
   - Review error messages don't leak sensitive info

**Tools**:
- AWS IAM Policy Simulator
- `git secrets` or `gitleaks` for secret scanning
- Manual code review

**Commit**:
```
security: harden DynamoDB access and Lambda permissions

- Apply least privilege to IAM policies
- Enable encryption for sensitive data
- Add input validation to API handlers
- Remove any hardcoded credentials
```

---

### T090: Performance Validation

**Purpose**: Ensure Agent Card discovery meets performance requirements (< 500ms for 100 agents)

**Approach**:
1. Create performance test script
2. Mock 100 agents with Agent Cards
3. Measure discovery time:
   ```python
   import time
   start = time.time()
   agents = discover_all_agents()
   duration = (time.time() - start) * 1000  # ms
   assert duration < 500, f"Discovery took {duration}ms (limit: 500ms)"
   ```
4. Profile slow operations (use `cProfile` or `py-spy`)
5. Optimize if needed:
   - Parallel Agent Card fetching
   - Caching
   - Connection pooling
6. Document performance characteristics

**Manual Validation**:
- Run performance test multiple times
- Check for consistency
- Test with varying agent counts (10, 50, 100, 200)
- Profile and identify bottlenecks

**Commit**:
```
perf(registry): optimize agent discovery for 100+ agents

- Add parallel Agent Card fetching
- Implement connection pooling
- Verified discovery < 500ms for 100 agents
- Added performance test suite
```

---

## Workflow for Manual Completion

1. **For Each Task**:
   - Read task description
   - Plan approach
   - Make changes
   - Run `/stop` (Enhanced Stop Hook validates tests)
   - If tests pass: Commits created automatically
   - If tests fail: Fix issues, retry

2. **Enhanced Stop Hook Benefits**:
   - Automatic test validation
   - Coverage enforcement
   - Conventional commit creation
   - Logical chunking

3. **No Ralph-Loop Needed**:
   - These tasks don't follow TDD pattern
   - Require subjective judgment
   - Need manual verification
   - Human oversight essential

## Success Criteria

- ✅ All tasks T084-T090 complete
- ✅ CI/CD pipeline functional
- ✅ Coverage at 80%+ overall
- ✅ All documentation examples work
- ✅ Security review passed
- ✅ Performance requirements met
- ✅ All tests pass
- ✅ All commits follow Constitution Principle VIII

## Expected Timeline

- **T084 (CI)**: ~2-3 hours
- **T085 (Coverage)**: ~1-2 hours
- **T086 (Integration)**: ~3-4 hours
- **T087 (Quickstart)**: ~1-2 hours
- **T088 (Cleanup)**: ~2-3 hours
- **T089 (Security)**: ~3-4 hours
- **T090 (Performance)**: ~2-3 hours

**Total**: ~14-21 hours of focused work

## Constitutional Compliance

This phase implements:
- ✅ **Principle I**: Following tasks.md from spec.md
- ✅ **Principle III**: Stop hook ensures verification before commits
- ✅ **Principle VI**: Human oversight for quality tasks
- ✅ **Principle VIII**: Conventional commits via Stop hook

## Final Coverage Target

After Phase 8 completion:
- Overall coverage: **80%+**
- All modules: **>= 80%** (or explicit pragma exclusions)
- Integration tests: Documented as skipped in local runs, functional in CI

## Notes

- Use Enhanced Stop Hook for all commits
- No need for ralph-loop - these tasks benefit from human judgment
- Take time to do thorough reviews
- Don't rush security and performance validation
- Document any deviations or decisions made

## Quick Reference

**Run all tests**:
```bash
source .venv/bin/activate && pytest -v
```

**Run with coverage**:
```bash
source .venv/bin/activate && pytest --cov=src --cov-report=html
```

**View coverage report**:
```bash
open htmlcov/index.html  # macOS
```

**Run security scan**:
```bash
git secrets --scan  # if configured
```

**Profile performance**:
```bash
python -m cProfile -o profile.stats your_script.py
python -m pstats profile.stats
```
