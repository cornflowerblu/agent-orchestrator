# Tasks: Autonomous Loop Execution

**Input**: Design documents from `/specs/002-autonomous-loop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included following the project's TDD workflow and Constitution Principle III (Verification-First).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module directories and extend existing structure

- [x] T001 Create src/loop/ directory structure with __init__.py
- [x] T002 [P] Create src/orchestrator/ directory structure with __init__.py
- [x] T003 [P] Create src/dashboard/ directory structure with __init__.py
- [x] T004 [P] Create tests/unit/test_loop/ directory structure
- [x] T005 [P] Create tests/integration/test_loop/ directory structure
- [x] T006 Add loop framework dependencies to pyproject.toml (opentelemetry-api, opentelemetry-sdk)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and exceptions that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Enums and Base Types

- [x] T007 [P] Create ExitConditionType enum in src/loop/models.py
- [x] T008 [P] Create ExitConditionStatusValue enum in src/loop/models.py
- [x] T009 [P] Create LoopPhase enum in src/loop/models.py
- [x] T010 [P] Create LoopOutcome enum in src/loop/models.py
- [x] T011 [P] Create IterationEventType enum in src/loop/models.py

### Core Models (shared across stories)

- [x] T012 [P] Create ExitConditionConfig model in src/loop/models.py
- [x] T013 [P] Create ExitConditionStatus model in src/loop/models.py
- [x] T014 Create LoopConfig model in src/loop/models.py (depends on T007, T012)
- [x] T015 [P] Create IterationEvent model in src/loop/models.py (depends on T011, T009)
- [x] T016 [P] Create LoopResult model in src/loop/models.py (depends on T010, T013)

### Exceptions

- [x] T017 Add LoopFrameworkError base exception to src/exceptions.py
- [x] T018 [P] Add PolicyViolationError exception to src/exceptions.py
- [x] T019 [P] Add CheckpointRecoveryError exception to src/exceptions.py
- [x] T020 [P] Add ExitConditionEvaluationError exception to src/exceptions.py

### Unit Tests for Foundational Models

- [x] T021 [P] Write unit tests for all enums in tests/unit/test_loop/test_models.py
- [x] T022 [P] Write unit tests for LoopConfig validation in tests/unit/test_loop/test_models.py
- [x] T023 Write unit tests for ExitConditionStatus methods in tests/unit/test_loop/test_models.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Agent Implements Autonomous Loop with Framework (Priority: P1)

**Goal**: Enable agents to use the Loop Framework for autonomous execution with standard patterns

**Independent Test**: Initialize Loop Framework with default config, run iterations, verify helper methods available

### Implementation for User Story 1

- [x] T024 [US1] Create LoopState model in src/loop/models.py with state tracking methods
- [x] T025 [US1] Create LoopFramework class skeleton in src/loop/framework.py
- [x] T026 [US1] Implement LoopFramework.initialize() async method in src/loop/framework.py
- [x] T027 [US1] Implement LoopFramework.initialize_sync() method in src/loop/framework.py
- [x] T028 [US1] Implement LoopFramework.run() main loop logic in src/loop/framework.py
- [x] T029 [US1] Implement LoopFramework.get_state() method in src/loop/framework.py
- [x] T030 [US1] Implement LoopFramework.get_exit_condition_status() method in src/loop/framework.py
- [x] T031 [US1] Implement iteration execution with work_function callback in src/loop/framework.py
- [x] T032 [US1] Implement loop termination logic (conditions met, iteration limit) in src/loop/framework.py
- [x] T033 [US1] Implement re-entry prevention (is_active flag) in src/loop/framework.py
- [x] T034 [US1] Add OTEL tracer setup in LoopFramework.__init__ in src/loop/framework.py
- [x] T035 [US1] Implement LoopFramework.emit_event() for Observability in src/loop/framework.py

### Unit Tests for User Story 1

- [x] T036 [P] [US1] Write unit tests for LoopState model in tests/unit/test_loop/test_models.py
- [x] T037 [P] [US1] Write unit tests for LoopFramework initialization in tests/unit/test_loop/test_framework.py
- [x] T038 [US1] Write unit tests for LoopFramework.run() in tests/unit/test_loop/test_framework.py
- [x] T039 [US1] Write unit tests for loop termination conditions in tests/unit/test_loop/test_framework.py
- [x] T040 [US1] Write unit tests for re-entry prevention in tests/unit/test_loop/test_framework.py

**Checkpoint**: User Story 1 complete - agents can implement basic autonomous loops

---

## Phase 4: User Story 3 - Agent Evaluates Exit Conditions via Verification Tools (Priority: P1)

**Goal**: Enable agents to evaluate exit conditions using Gateway/Code Interpreter verification tools

**Independent Test**: Invoke pytest via Code Interpreter, evaluate condition, verify status marked correctly

### Implementation for User Story 3

- [x] T041 [US3] Create ExitConditionEvaluator class skeleton in src/loop/conditions.py
- [x] T042 [US3] Implement Code Interpreter client wrapper in src/loop/conditions.py
- [x] T043 [US3] Implement evaluate_tests() method (ALL_TESTS_PASS) in src/loop/conditions.py
- [x] T044 [US3] Implement evaluate_linting() method (LINTING_CLEAN) in src/loop/conditions.py
- [x] T045 [US3] Implement evaluate_build() method (BUILD_SUCCEEDS) in src/loop/conditions.py
- [x] T046 [US3] Implement evaluate_security_scan() method (SECURITY_SCAN_CLEAN) in src/loop/conditions.py
- [x] T047 [US3] Implement evaluate_custom() method for CUSTOM type in src/loop/conditions.py
- [x] T048 [US3] Implement evaluate() dispatcher method in src/loop/conditions.py
- [x] T049 [US3] Implement Gateway tool discovery for MCP tools in src/loop/conditions.py
- [x] T050 [US3] Implement Gateway tool invocation wrapper in src/loop/conditions.py
- [x] T051 [US3] Add timeout handling (30s per tool per SC-002) in src/loop/conditions.py
- [ ] T052 [US3] Integrate ExitConditionEvaluator with LoopFramework in src/loop/framework.py
- [ ] T053 [US3] Implement LoopFramework.evaluate_all_conditions() in src/loop/framework.py

### Unit Tests for User Story 3

- [x] T054 [P] [US3] Write unit tests for ExitConditionEvaluator in tests/unit/test_loop/test_conditions.py
- [x] T055 [P] [US3] Write unit tests for evaluate_tests() in tests/unit/test_loop/test_conditions.py
- [x] T056 [P] [US3] Write unit tests for evaluate_linting() in tests/unit/test_loop/test_conditions.py
- [x] T057 [US3] Write unit tests for timeout handling in tests/unit/test_loop/test_conditions.py
- [x] T058 [US3] Write integration test for Code Interpreter in tests/integration/test_loop/test_conditions.py

**Checkpoint**: User Story 3 complete - agents can evaluate exit conditions via verification tools

---

## Phase 5: User Story 2 - Agent Saves Checkpoints to Memory Service (Priority: P2)

**Goal**: Enable agents to save/recover checkpoints via AgentCore Memory service

**Independent Test**: Save checkpoint every N iterations, simulate interruption, recover from Memory

### Implementation for User Story 2

- [x] T059 [US2] Create Checkpoint model in src/loop/models.py
- [x] T060 [US2] Implement Checkpoint.from_loop_state() class method in src/loop/models.py
- [x] T061 [US2] Implement Checkpoint.to_loop_state() method in src/loop/models.py
- [x] T062 [US2] Create CheckpointManager class skeleton in src/loop/checkpoint.py
- [x] T063 [US2] Implement Memory client wrapper in src/loop/checkpoint.py
- [x] T064 [US2] Implement CheckpointManager.create_memory() for session in src/loop/checkpoint.py
- [x] T065 [US2] Implement CheckpointManager.save_checkpoint() in src/loop/checkpoint.py
- [x] T066 [US2] Implement CheckpointManager.load_checkpoint() in src/loop/checkpoint.py
- [x] T067 [US2] Implement CheckpointManager.list_checkpoints() in src/loop/checkpoint.py
- [x] T068 [US2] Add checkpoint interval logic to LoopFramework.run() in src/loop/framework.py
- [x] T069 [US2] Implement LoopFramework.save_checkpoint() helper in src/loop/framework.py
- [x] T070 [US2] Implement LoopFramework.load_checkpoint() helper in src/loop/framework.py
- [x] T071 [US2] Add resume_from parameter to LoopFramework.run() in src/loop/framework.py

### Unit Tests for User Story 2

- [x] T072 [P] [US2] Write unit tests for Checkpoint model in tests/unit/test_loop/test_models.py
- [x] T073 [P] [US2] Write unit tests for CheckpointManager in tests/unit/test_loop/test_checkpoint.py
- [ ] T074 [US2] Write unit tests for checkpoint interval logic in tests/unit/test_loop/test_framework.py
- [ ] T075 [US2] Write integration test for Memory service in tests/integration/test_loop/test_checkpoint.py

**Checkpoint**: User Story 2 complete - agents can save/recover checkpoints

---

## Phase 6: User Story 4 - Orchestrator Enforces Iteration Limits via Policy (Priority: P2)

**Goal**: Enable Policy service to enforce iteration limits using Cedar rules

**Independent Test**: Configure Policy with low limit, run agent, verify Policy stops agent

### Implementation for User Story 4

- [x] T076 [US4] Create PolicyConfig model in src/orchestrator/models.py
- [x] T077 [US4] Implement PolicyConfig.generate_cedar_statement() in src/orchestrator/models.py
- [x] T078 [US4] Create PolicyEnforcer class skeleton in src/orchestrator/policy.py
- [x] T079 [US4] Implement Policy client wrapper in src/orchestrator/policy.py
- [x] T080 [US4] Implement PolicyEnforcer.create_iteration_policy() in src/orchestrator/policy.py
- [x] T081 [US4] Implement PolicyEnforcer.check_iteration_allowed() in src/orchestrator/policy.py
- [x] T082 [US4] Implement PolicyEnforcer.update_policy() in src/orchestrator/policy.py
- [x] T083 [US4] Implement PolicyEnforcer.get_policy() in src/orchestrator/policy.py
- [x] T084 [US4] Create AlertManager class in src/orchestrator/alerts.py
- [x] T085 [US4] Implement AlertManager.send_warning() for 80% threshold in src/orchestrator/alerts.py
- [x] T086 [US4] Create ObservabilityMonitor class skeleton in src/orchestrator/monitor.py
- [x] T087 [US4] Implement ObservabilityMonitor.watch_agent() in src/orchestrator/monitor.py
- [x] T088 [US4] Implement threshold detection logic (SC-008: 80%) in src/orchestrator/monitor.py
- [x] T089 [US4] Integrate PolicyEnforcer with LoopFramework in src/loop/framework.py
- [x] T090 [US4] Add PolicyViolation handling to LoopFramework.run() in src/loop/framework.py

### Unit Tests for User Story 4

- [x] T091 [P] [US4] Write unit tests for PolicyConfig in tests/unit/test_orchestrator/test_models.py
- [x] T092 [P] [US4] Write unit tests for PolicyEnforcer in tests/unit/test_orchestrator/test_policy.py
- [x] T093 [P] [US4] Write unit tests for AlertManager in tests/unit/test_orchestrator/test_alerts.py
- [x] T094 [US4] Write unit tests for ObservabilityMonitor in tests/unit/test_orchestrator/test_monitor.py
- [x] T095 [US4] Write integration test for Policy service in tests/integration/test_orchestrator/test_policy.py

**Checkpoint**: User Story 4 complete - iteration limits enforced via Policy

---

## Phase 7: User Story 5 - Human Views Agent Loop Progress via Observability (Priority: P3)

**Goal**: Enable dashboard queries to AgentCore Observability for real-time progress

**Independent Test**: Run agent, query Observability API, verify progress displayed

### Implementation for User Story 5

- [x] T096 [US5] Create ObservabilityQueries class skeleton in src/dashboard/queries.py
- [x] T097 [US5] Implement CloudWatch/X-Ray client wrapper in src/dashboard/queries.py
- [x] T098 [US5] Implement ObservabilityQueries.get_loop_progress() in src/dashboard/queries.py
- [x] T099 [US5] Implement ObservabilityQueries.get_recent_events() in src/dashboard/queries.py
- [x] T100 [US5] Implement ObservabilityQueries.list_checkpoints() in src/dashboard/queries.py
- [x] T101 [US5] Implement ObservabilityQueries.get_exit_condition_history() in src/dashboard/queries.py
- [x] T102 [US5] Create LoopProgress response model in src/dashboard/models.py
- [ ] T103 [US5] Implement streaming/subscription logic in src/dashboard/queries.py
- [x] T104 [US5] Create API handlers skeleton in src/dashboard/handlers.py
- [x] T105 [US5] Implement /progress/{session_id} handler in src/dashboard/handlers.py
- [x] T106 [US5] Implement /events/{session_id} handler in src/dashboard/handlers.py
- [x] T107 [US5] Implement /checkpoints/{session_id} handler in src/dashboard/handlers.py

### Unit Tests for User Story 5

- [x] T108 [P] [US5] Write unit tests for ObservabilityQueries in tests/unit/test_dashboard/test_queries.py
- [x] T109 [P] [US5] Write unit tests for LoopProgress model in tests/unit/test_dashboard/test_models.py
- [x] T110 [US5] Write unit tests for API handlers in tests/unit/test_dashboard/test_handlers.py
- [x] T111 [US5] Write integration test for Observability API in tests/integration/test_dashboard/test_queries.py

**Checkpoint**: User Story 5 complete - dashboard can query progress via Observability

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T112 [P] Add type hints and docstrings to all public APIs in src/loop/
- [ ] T113 [P] Add type hints and docstrings to all public APIs in src/orchestrator/
- [ ] T114 [P] Add type hints and docstrings to all public APIs in src/dashboard/
- [ ] T115 [P] Create src/loop/__init__.py with public exports
- [ ] T116 [P] Create src/orchestrator/__init__.py with public exports
- [ ] T117 [P] Create src/dashboard/__init__.py with public exports
- [ ] T118 Run ruff format on all new files
- [ ] T119 Run ruff check and fix any linting issues
- [ ] T120 Validate quickstart.md examples work with implementation
- [ ] T121 Run full test suite and ensure 80% coverage on new code
- [ ] T122 Create infrastructure/cdk/stacks/loop_stack.py for Cedar policies

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
     ↓
Phase 2 (Foundational) ─── BLOCKS ALL USER STORIES
     ↓
┌────┴────┐
↓         ↓
Phase 3   Phase 4     ← US1 and US3 can run in PARALLEL (both P1)
(US1)     (US3)
  ↓         ↓
  └────┬────┘
       ↓
┌──────┴──────┐
↓             ↓
Phase 5     Phase 6   ← US2 and US4 can run in PARALLEL (both P2)
(US2)       (US4)
  ↓           ↓
  └─────┬─────┘
        ↓
    Phase 7           ← US5 depends on all above
    (US5)
        ↓
    Phase 8
    (Polish)
```

### User Story Dependencies

| Story | Priority | Depends On | Can Parallel With |
|-------|----------|------------|-------------------|
| US1 | P1 | Foundational only | US3 |
| US3 | P1 | Foundational only | US1 |
| US2 | P2 | US1 (LoopState) | US4 |
| US4 | P2 | US1 (LoopFramework) | US2 |
| US5 | P3 | US1, US2, US4 (needs data) | None |

### Parallel Execution Opportunities

**Phase 1 Setup**: T002, T003, T004, T005 (different directories)

**Phase 2 Foundational**:
- T007-T011 (all enums, different definitions)
- T012-T016 (models, after enums)
- T017-T020 (exceptions, independent)
- T021-T023 (tests, after models)

**After Foundational**:
- US1 + US3 in parallel (both P1, different modules)

**After US1+US3**:
- US2 + US4 in parallel (both P2, different modules)

---

## Parallel Example: US1 + US3

```bash
# After Phase 2 completes, launch in parallel:

# Terminal 1 (or worktree 1):
/ralph "Implement US1 tasks T024-T040" --max-iterations 50

# Terminal 2 (or worktree 2):
/ralph "Implement US3 tasks T041-T058" --max-iterations 50
```

---

## Implementation Strategy

### MVP First (US1 + US3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (basic loop framework)
4. Complete Phase 4: User Story 3 (exit condition evaluation)
5. **STOP and VALIDATE**: Test loop with exit conditions independently
6. Deploy/demo if ready

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 + US3 → Agents can run autonomous loops with exit conditions
2. **Resilient MVP**: Add US2 → Agents can recover from interruptions
3. **Governed MVP**: Add US4 → Iteration limits enforced by Policy
4. **Observable MVP**: Add US5 → Human operators can monitor progress

### Parallel Team Strategy

With 2-3 developers:

1. All complete Setup + Foundational together
2. Once Foundational done:
   - Developer A: US1 (LoopFramework)
   - Developer B: US3 (ExitConditionEvaluator)
3. After US1+US3:
   - Developer A: US2 (CheckpointManager)
   - Developer B: US4 (PolicyEnforcer)
4. Developer A or B: US5 (Dashboard)
5. All: Polish phase

---

## Task Summary

| Phase | Story | Task Count | Parallel Tasks |
|-------|-------|------------|----------------|
| 1 | Setup | 6 | 4 |
| 2 | Foundational | 17 | 14 |
| 3 | US1 | 17 | 2 |
| 4 | US3 | 18 | 3 |
| 5 | US2 | 17 | 2 |
| 6 | US4 | 20 | 3 |
| 7 | US5 | 16 | 2 |
| 8 | Polish | 11 | 6 |
| **Total** | | **122** | **36** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
