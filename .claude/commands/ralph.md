---
description: Start an autonomous TDD loop that continues until completion criteria are met or max iterations reached
---

## User Input

```text
$ARGUMENTS
```

## Ralph Loop - Autonomous TDD Workflow

This skill implements a self-correcting development loop that:
1. Executes a task prompt (often `/speckit.implement`)
2. Validates tests via the Stop hook
3. Continues iterating until completion promise is found
4. Respects max-iterations safety limit

## Parsing Arguments

Parse the user input to extract:
- **prompt**: The task to execute (everything before `--`)
- **completion-promise**: The text that signals completion (default: `COMPLETE`)
- **max-iterations**: Maximum iterations before stopping (default: 50)

Example: `/ralph "/speckit.implement Phase 6" --completion-promise "PHASE_US4_COMPLETE" --max-iterations 75`

## Loop Execution

### Initialize Loop State

```
ITERATION = 0
MAX_ITERATIONS = [parsed max-iterations or 50]
COMPLETION_PROMISE = [parsed completion-promise or "COMPLETE"]
PROMPT = [parsed prompt]
LOOP_ACTIVE = true
```

### Main Loop

**While LOOP_ACTIVE and ITERATION < MAX_ITERATIONS:**

1. **Increment iteration**: `ITERATION += 1`

2. **Display iteration header**:
   ```
   ════════════════════════════════════════════════════════
   RALPH LOOP - Iteration {ITERATION}/{MAX_ITERATIONS}
   ════════════════════════════════════════════════════════
   Completion Promise: {COMPLETION_PROMISE}
   ```

3. **Execute the prompt**:
   - If prompt starts with `/`, invoke that skill (e.g., `/speckit.implement`)
   - Otherwise, execute the prompt as a direct task
   - Work on the task following TDD workflow:
     - Write failing tests first (if applicable)
     - Implement code to pass tests
     - Refactor for quality

4. **Run test validation**:
   ```bash
   source .venv/bin/activate && pytest --cov=src --cov-report=term-missing -m "not integration and not sam_local"
   ```

5. **Check test results**:
   - If tests FAIL: Continue to next iteration (loop will retry)
   - If tests PASS: Check for completion

6. **Check completion criteria**:
   - Review the work done in this iteration
   - Determine if ALL tasks in the prompt scope are complete
   - Determine if coverage requirements are met (80%+)

7. **If ALL completion criteria met**:
   - Output the completion promise: `<promise>{COMPLETION_PROMISE}</promise>`
   - Set `LOOP_ACTIVE = false`
   - Display success summary

8. **If NOT complete**:
   - Display progress summary for this iteration
   - Continue to next iteration

### Iteration Summary (after each iteration)

Display:
```
────────────────────────────────────────────────────────
Iteration {ITERATION} Summary
────────────────────────────────────────────────────────
Tests: [PASS/FAIL] ([X] passed, [Y] failed, [Z] skipped)
Coverage: [XX.X]% (target: 80%)
Tasks completed this iteration: [list]
Tasks remaining: [list]
Status: [CONTINUING / COMPLETE / MAX_ITERATIONS_REACHED]
────────────────────────────────────────────────────────
```

### Exit Conditions

The loop exits when ANY of these conditions are met:

1. **Completion Promise Found** (SUCCESS):
   - All tasks in scope are complete
   - Tests pass
   - Coverage adequate
   - Output: `<promise>{COMPLETION_PROMISE}</promise>`

2. **Max Iterations Reached** (SAFETY EXIT):
   - Display progress summary
   - List completed vs remaining tasks
   - Suggest next steps
   - Do NOT output completion promise

3. **User Interruption** (MANUAL EXIT):
   - User presses Ctrl+C or sends interrupt
   - Save progress state
   - Allow resume later

### Final Output

**On Success:**
```
════════════════════════════════════════════════════════
RALPH LOOP COMPLETE
════════════════════════════════════════════════════════
Total iterations: {ITERATION}
Final coverage: {XX.X}%
All tasks complete: YES

<promise>{COMPLETION_PROMISE}</promise>
════════════════════════════════════════════════════════
```

**On Max Iterations:**
```
════════════════════════════════════════════════════════
RALPH LOOP - MAX ITERATIONS REACHED
════════════════════════════════════════════════════════
Total iterations: {MAX_ITERATIONS}
Current coverage: {XX.X}%
Tasks completed: [list]
Tasks remaining: [list]

Next steps:
1. Review remaining tasks
2. Run /ralph again to continue
3. Or complete manually

(No completion promise output - loop did not complete)
════════════════════════════════════════════════════════
```

## TDD Workflow Within Each Iteration

When executing tasks, follow Test-Driven Development:

1. **Read the task** from tasks.md
2. **Write failing test first** (if test doesn't exist)
3. **Implement minimum code** to pass the test
4. **Run tests** to verify
5. **Refactor** for quality (if tests pass)
6. **Commit** logical chunks (see commit rules below)
7. **Mark task complete** in tasks.md
8. **Move to next task**

## Commit Rules (Constitution Principle VIII)

When tests pass and work is ready to commit, create **logical chunk commits**:

**Commit Message Format**:
```
<type>[optional scope]: <description>
```

**Types**: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

**Logical Chunks** - Create MULTIPLE commits, one per:
- Model/entity created
- Service implemented
- API endpoint added
- Test suite added
- Config vs implementation (separate)

**Never batch unrelated changes into a single commit.**

Example:
```
feat(consultation): add ConsultationPhase enum
feat(consultation): add ConsultationCondition model
test(consultation): add unit tests for consultation rules
```

## Example Usage

```bash
# Phase 6 implementation
/ralph "/speckit.implement Phase 6 tasks (T050-T061)" --completion-promise "PHASE_US4_COMPLETE" --max-iterations 75

# Phase 7 implementation
/ralph "/speckit.implement Phase 7 tasks (T062-T083)" --completion-promise "PHASE_US5_COMPLETE" --max-iterations 100

# Simple task with default settings
/ralph "Implement the authentication module"
```

## Constitutional Compliance

This skill implements:
- **Principle III (Verification-First)**: Tests validated each iteration
- **Principle VI (Autonomous with Oversight)**: Max-iterations safety limit
- **Principle VIII (Conventional Commits)**: Logical chunk commits after tests pass
