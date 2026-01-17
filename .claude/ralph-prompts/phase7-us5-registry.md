# Ralph Loop: Phase 7 - User Story 5 Registry API

Implement tasks T062-T083 following TDD workflow to build the agent registry query interface.

## Context

This phase implements the Agent Registry Query Interface - an orchestrator-facing API to query agents by skills, input compatibility, and consultation requirements. This builds on Agent Cards (US1), Enhanced Metadata (US3), and Consultation Requirements (US4) to provide a unified discovery and compatibility checking system.

## Tasks (22 Total)

### Test Tasks (Complete First)
- [ ] T062 - Unit test for agent discovery in tests/unit/test_discovery.py
- [ ] T063 - Unit test for agent query interface in tests/unit/test_query.py
- [ ] T064 - Integration test for registry API in tests/integration/test_registry_api.py

### Discovery Implementation
- [ ] T065 - Implement A2A Agent Card discovery in src/registry/discovery.py
- [ ] T066 - Implement fetch_agent_card from /.well-known/agent-card.json in src/registry/discovery.py
- [ ] T067 - Implement discover_all_agents via A2A protocol in src/registry/discovery.py

### Query Interface Implementation
- [ ] T068 - Create AgentRegistry class in src/registry/query.py
- [ ] T069 - Implement find_by_skill method in src/registry/query.py
- [ ] T070 - Implement find_by_input_compatibility method in src/registry/query.py
- [ ] T071 - Implement check_compatibility method in src/registry/query.py
- [ ] T072 - Implement get_consultation_requirements method in src/registry/query.py

### Status Tracking
- [ ] T073 - Create AgentStatus Pydantic model in src/registry/models.py
- [ ] T074 - Implement status tracking storage in src/registry/status.py

### API Infrastructure
- [ ] T075 - Create API stack with Lambda + API Gateway in infrastructure/cdk/stacks/api_stack.py

### Lambda Handlers (8 handlers)
- [ ] T076 - Implement listAgents Lambda handler in src/registry/handlers.py
- [ ] T077 - Implement getAgent Lambda handler in src/registry/handlers.py
- [ ] T078 - Implement updateAgentMetadata Lambda handler in src/registry/handlers.py
- [ ] T079 - Implement getConsultationRequirements Lambda handler in src/registry/handlers.py
- [ ] T080 - Implement checkCompatibility Lambda handler in src/registry/handlers.py
- [ ] T081 - Implement findCompatibleAgents Lambda handler in src/registry/handlers.py
- [ ] T082 - Implement getAgentStatus Lambda handler in src/registry/handlers.py
- [ ] T083 - Implement updateAgentStatus Lambda handler in src/registry/handlers.py

## TDD Workflow (MANDATORY)

For each task, follow this exact sequence:

1. **Write Failing Test First** (if not already written)
   - Create test file if needed
   - Write test cases that will fail initially
   - Run tests to confirm they fail for the right reason

2. **Implement Minimum Code to Pass Test**
   - Create only the code needed to make the test pass
   - Don't add extra features or "nice-to-haves"
   - Focus on making the test green

3. **Run Tests with Coverage**
   ```bash
   source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration" -v
   ```
   - If tests fail: Analyze output, fix implementation, retry
   - If coverage < 80%: Write additional tests, retry
   - Integration test (T064) is expected to skip (requires AWS deployment)

4. **Refactor for Quality**
   - Clean up code while keeping tests green
   - Improve naming, structure, documentation
   - Ensure compliance with Constitution principles

5. **Commit Logical Chunk (Constitution Principle VIII)**
   - Use conventional commit format: `<type>[scope]: <description>`
   - Create separate commits for:
     - Each discovery method implemented
     - Each query method implemented
     - Each Lambda handler implemented
     - Test suites added
     - Infrastructure code
   - Examples:
     - `feat(registry): add agent discovery via A2A protocol`
     - `feat(registry): implement find_by_skill query method`
     - `feat(registry): add listAgents Lambda handler`
     - `feat(infra): create registry API stack with Lambda and API Gateway`
     - `test(registry): add unit tests for agent discovery`

6. **Stop Hook Runs Automatically**
   - After each commit attempt, the Stop hook will:
     - Run tests automatically
     - Validate coverage >= 80%
     - Block commit if tests fail or coverage insufficient
   - If blocked: Fix the issue and retry

7. **Repeat Until ALL Tasks Complete**

## Coverage Backfill Requirements

**CRITICAL**: This phase MUST backfill missing test coverage from earlier modules:

### src/metadata/storage.py (Currently 0% → Target 80%)
- Add tests for DynamoDB operations
- Add tests for error handling (connection failures, invalid data)
- Add tests for metadata CRUD operations

### src/gateway/tools.py (Currently 40% → Target 80%)
- Add tests for MCP client integration
- Add tests for tool discovery
- Add tests for tool invocation
- Add tests for error handling

### New Modules (Target 100%)
- `src/registry/discovery.py` - 100% coverage
- `src/registry/query.py` - 100% coverage
- `src/registry/models.py` - 100% coverage
- `src/registry/status.py` - 100% coverage
- `src/registry/handlers.py` - 100% coverage

## Completion Criteria (ALL Must Be Met)

- ✅ All tasks T062-T083 complete
- ✅ All tests pass (pytest exit code 0)
- ✅ Coverage >= 75% overall (phase target; final target 80% in Phase 8)
- ✅ `src/metadata/storage.py` coverage >= 80%
- ✅ `src/gateway/tools.py` coverage >= 80%
- ✅ All registry modules have 100% coverage
- ✅ All logical chunks committed following Constitution Principle VIII
- ✅ No uncommitted changes remaining

## Output When Complete

When ALL completion criteria are met, output:

```
<promise>PHASE_US5_COMPLETE</promise>
```

**CRITICAL**: Do NOT output the completion promise unless ALL criteria above are met. The ralph-loop will only exit when it sees this exact promise.

## Safety Limits

- **Max Iterations**: 100
- **Escalation Point**: If stuck after 70 iterations, output progress summary:
  ```
  🔴 Blocked after 70 iterations

  Progress:
  ✅ Completed: T062, T063, T065, ...
  🔴 Blocked on: T0XX (description of issue)
  ⏸️  Not started: T0YY, T0ZZ, ...

  Test status: X passing, Y failing
  Coverage: Z% (target: 75%)

  Coverage by module:
  - src/registry/discovery.py: X%
  - src/registry/query.py: X%
  - src/metadata/storage.py: X% (need 80%)
  - src/gateway/tools.py: X% (need 80%)

  Issue: [Describe the blocking issue]

  Escalating for human review.
  ```

## Constitutional Compliance

This implementation MUST follow:

- **Principle I**: All work follows tasks.md derived from spec.md
- **Principle III**: Tests MUST pass before marking task complete
- **Principle VII**: Use AgentCore Gateway and A2A protocol for agent discovery
- **Principle VIII**: Conventional commits with logical chunks

## Expected Coverage Improvement

- **Starting Coverage**: 60-65% (after Phase 6)
- **Phase 7 Target**: 75-80%
- **Key Improvements**:
  - `src/metadata/storage.py`: 0% → 80%
  - `src/gateway/tools.py`: 40% → 80%
  - `src/registry/*`: All new files at 100%

## Notes

- Integration test (T064) is expected to skip - this is correct behavior
- Focus on comprehensive unit tests (T062, T063) to drive implementation
- Registry should integrate with AgentCore A2A protocol for discovery
- Lambda handlers should follow AWS Lambda best practices
- CDK infrastructure should use AWS CDK Python constructs
- All models should use Pydantic for validation
- Follow existing code patterns from earlier phases

## Task Grouping Strategy

**Group 1 - Discovery (Tasks T062, T065-T067)**:
- Write discovery tests first
- Implement A2A protocol integration
- Test against mock Agent Cards
- ~15-20 iterations

**Group 2 - Query Interface (Tasks T063, T068-T072)**:
- Write query tests first
- Implement registry class and query methods
- Test compatibility checking logic
- ~20-25 iterations

**Group 3 - Status & Models (Tasks T073-T074)**:
- Write model tests
- Implement status tracking
- ~10-15 iterations

**Group 4 - API Infrastructure (Task T075)**:
- Create CDK stack
- Define API Gateway and Lambda configuration
- ~5-10 iterations

**Group 5 - Lambda Handlers (Tasks T076-T083)**:
- Implement one handler at a time
- Test each handler independently
- ~25-30 iterations (8 handlers)

**Group 6 - Coverage Backfill**:
- Add tests for src/metadata/storage.py
- Add tests for src/gateway/tools.py
- ~15-20 iterations

## Quick Reference

**Run tests**:
```bash
source .venv/bin/activate && pytest -v
```

**Run with coverage**:
```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration"
```

**Check coverage for specific modules**:
```bash
source .venv/bin/activate && pytest --cov=src/registry --cov=src/metadata --cov=src/gateway --cov-report=term-missing
```

**Run only registry tests**:
```bash
source .venv/bin/activate && pytest tests/unit/test_discovery.py tests/unit/test_query.py -v
```

**Check what needs coverage**:
```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing | grep -E "(storage|tools|registry)"
```
