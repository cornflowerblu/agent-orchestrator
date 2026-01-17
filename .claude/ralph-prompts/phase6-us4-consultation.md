# Ralph Loop: Phase 6 - User Story 4 Consultation Requirements

Implement tasks T050-T061 following TDD workflow to build the consultation requirements system.

## Context

This phase implements the consultation protocol layer - a custom extension on top of AgentCore that declares mandatory/optional agent consultations. This ensures cross-functional review and prevents siloed decision-making (Constitution Principle V).

## Tasks (12 Total)

### Test Tasks (Complete First)
- [ ] T050 - Unit test for consultation rules in tests/unit/test_consultation_rules.py
- [ ] T051 - Integration test for consultation enforcement in tests/integration/test_consultation_enforcement.py

### Model Tasks
- [ ] T052 - Create ConsultationPhase enum in src/consultation/rules.py
- [ ] T053 - Create ConsultationCondition Pydantic model in src/consultation/rules.py
- [ ] T054 - Create ConsultationRequirement Pydantic model in src/consultation/rules.py
- [ ] T055 - Create ConsultationOutcome Pydantic model in src/consultation/rules.py

### Implementation Tasks
- [ ] T056 - Implement ConsultationEngine class in src/consultation/enforcement.py
- [ ] T057 - Implement get_requirements method in src/consultation/enforcement.py
- [ ] T058 - Implement evaluate_condition method for conditional consultations in src/consultation/enforcement.py
- [ ] T059 - Implement query_observability_traces for A2A consultation verification in src/consultation/enforcement.py
- [ ] T060 - Implement validate_task_completion that blocks on missing consultations in src/consultation/enforcement.py
- [ ] T061 - Add consultation requirements to CustomAgentMetadata storage in src/metadata/storage.py

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
   - Integration tests (T051) are expected to skip (require AWS deployment)

4. **Refactor for Quality**
   - Clean up code while keeping tests green
   - Improve naming, structure, documentation
   - Ensure compliance with Constitution principles

5. **Commit Logical Chunk (Constitution Principle VIII)**
   - Use conventional commit format: `<type>[scope]: <description>`
   - Create separate commits for:
     - Each model/enum created
     - Each method implemented
     - Test suites added
   - Examples:
     - `feat(consultation): add ConsultationPhase enum`
     - `feat(consultation): add ConsultationCondition model`
     - `feat(consultation): implement get_requirements method`
     - `test(consultation): add unit tests for consultation rules`

6. **Stop Hook Runs Automatically**
   - After each commit attempt, the Stop hook will:
     - Run tests automatically
     - Validate coverage >= 80%
     - Block commit if tests fail or coverage insufficient
   - If blocked: Fix the issue and retry

7. **Repeat Until ALL Tasks Complete**

## Completion Criteria (ALL Must Be Met)

- ✅ All tasks T050-T061 complete
- ✅ All tests pass (pytest exit code 0)
- ✅ Coverage >= 60% (phase target; final target 80% in Phase 7)
- ✅ All logical chunks committed following Constitution Principle VIII
- ✅ No uncommitted changes remaining

## Output When Complete

When ALL completion criteria are met, output:

```
<promise>PHASE_US4_COMPLETE</promise>
```

**CRITICAL**: Do NOT output the completion promise unless ALL criteria above are met. The ralph-loop will only exit when it sees this exact promise.

## Safety Limits

- **Max Iterations**: 75
- **Escalation Point**: If stuck after 50 iterations, output progress summary:
  ```
  🔴 Blocked after 50 iterations

  Progress:
  ✅ Completed: T050, T051, T052, ...
  🔴 Blocked on: T0XX (description of issue)
  ⏸️  Not started: T0YY, T0ZZ, ...

  Test status: X passing, Y failing
  Coverage: Z% (target: 60%)

  Issue: [Describe the blocking issue]

  Escalating for human review.
  ```

## Constitutional Compliance

This implementation MUST follow:

- **Principle I**: All work follows tasks.md derived from spec.md
- **Principle III**: Tests MUST pass before marking task complete
- **Principle V**: Implementing the inter-agent consultation protocol
- **Principle VIII**: Conventional commits with logical chunks

## Expected Coverage Improvement

- **Starting Coverage**: 50.34%
- **Phase 6 Target**: 60-65%
- **New Code**:
  - `src/consultation/rules.py` - 100% coverage
  - `src/consultation/enforcement.py` - 100% coverage
  - Updated `src/metadata/storage.py` - improve from 0% to at least 50%

## Notes

- Integration test (T051) is expected to skip - this is correct behavior
- Focus on comprehensive unit tests (T050) to drive implementation
- Consultation engine should integrate with AgentCore Observability for A2A verification
- All models should use Pydantic for validation
- Follow existing code patterns from src/models/ and src/metadata/

## Quick Reference

**Run tests**:
```bash
source .venv/bin/activate && pytest -v
```

**Run with coverage**:
```bash
source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration"
```

**Check coverage for specific module**:
```bash
source .venv/bin/activate && pytest --cov=src/consultation --cov-report=term-missing
```

**Run only unit tests**:
```bash
source .venv/bin/activate && pytest tests/unit/ -v
```
