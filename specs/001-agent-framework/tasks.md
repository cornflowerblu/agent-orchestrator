# Tasks: Agent Framework

**Input**: Design documents from `/specs/001-agent-framework/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests ARE included as the spec mentions integration tests and the research.md documents a comprehensive CI/CD pipeline with test requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Infrastructure**: `infrastructure/cdk/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan with src/, tests/, infrastructure/ directories
- [ ] T002 Initialize Python 3.11+ project with pyproject.toml including bedrock-agentcore-sdk-python, strands, boto3, pydantic dependencies
- [ ] T003 [P] Configure ruff for linting and formatting in pyproject.toml
- [ ] T004 [P] Create .env.example with AWS_REGION, AGENT_METADATA_TABLE, AGENT_STATUS_TABLE, GATEWAY_URL
- [ ] T005 [P] Create pytest configuration in pyproject.toml with pytest-asyncio, pytest-cov, moto

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create base Pydantic models for SemanticType enum in src/metadata/models.py
- [ ] T007 [P] Create ValidationRule Pydantic model in src/metadata/models.py
- [ ] T008 Create CDK app entry point in infrastructure/cdk/app.py
- [ ] T009 [P] Create DynamoDB metadata stack with AgentMetadata table in infrastructure/cdk/stacks/metadata_stack.py
- [ ] T010 [P] Create DynamoDB status table with AgentStatus in infrastructure/cdk/stacks/metadata_stack.py
- [ ] T011 Create base exception classes in src/exceptions.py (AgentNotFoundError, ValidationError, ConsultationRequiredError)
- [ ] T012 [P] Create logging configuration in src/logging_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Define Agent with Agent Card (Priority: P1) 🎯 MVP

**Goal**: Platform administrators can define and deploy agents with A2A Agent Cards so the orchestrator can discover agent skills

**Independent Test**: Deploy an agent with Agent Card, query `/.well-known/agent-card.json`, verify skills discoverable via A2A protocol

### Tests for User Story 1

- [ ] T013 [P] [US1] Contract test for Agent Card schema validation in tests/contract/test_agent_card_schema.py
- [ ] T014 [P] [US1] Unit test for base agent class in tests/unit/test_base_agent.py

### Implementation for User Story 1

- [ ] T015 [P] [US1] Create Skill Pydantic model in src/agents/models.py
- [ ] T016 [P] [US1] Create AgentCard Pydantic model in src/agents/models.py
- [ ] T017 [US1] Create BaseAgent class with AgentCore Runtime integration in src/agents/base_agent.py
- [ ] T018 [US1] Implement Agent Card JSON loader from manifests in src/agents/base_agent.py
- [ ] T019 [P] [US1] Create Orchestrator agent manifest in src/agents/manifests/orchestrator.json
- [ ] T020 [P] [US1] Create Requirements agent manifest in src/agents/manifests/requirements.json
- [ ] T021 [P] [US1] Create Design agent manifest in src/agents/manifests/design.json
- [ ] T022 [P] [US1] Create Architect agent manifest in src/agents/manifests/architect.json
- [ ] T023 [P] [US1] Create Development agent manifest in src/agents/manifests/development.json
- [ ] T024 [P] [US1] Create Testing agent manifest in src/agents/manifests/testing.json
- [ ] T025 [P] [US1] Create Security agent manifest in src/agents/manifests/security.json
- [ ] T026 [P] [US1] Create Review agent manifest in src/agents/manifests/review.json
- [ ] T027 [P] [US1] Create UI/UX agent manifest in src/agents/manifests/uiux.json
- [ ] T028 [US1] Implement duplicate name validation in agent deployment in src/agents/base_agent.py
- [ ] T029 [US1] Implement Agent Card versioning support in src/agents/base_agent.py

**Checkpoint**: At this point, User Story 1 should be fully functional - agents can be defined with Agent Cards and deployed to AgentCore Runtime

---

## Phase 4: User Story 2 - Access Tools via Gateway (Priority: P1)

**Goal**: Agents can discover and access tools through AgentCore Gateway to interact with external APIs, Lambda functions, and MCP servers

**Independent Test**: Deploy Gateway with tool definitions, have agent call `mcp_client.list_tools_sync()`, verify tool discovery and invocation

### Tests for User Story 2

- [ ] T030 [P] [US2] Unit test for Gateway tool discovery helpers in tests/unit/test_gateway_tools.py
- [ ] T031 [P] [US2] Integration test for Gateway tool access in tests/integration/test_gateway_tools.py

### Implementation for User Story 2

- [ ] T032 [US2] Create MCPClient wrapper with sync methods in src/gateway/tools.py
- [ ] T033 [US2] Implement list_tools_sync helper in src/gateway/tools.py
- [ ] T034 [US2] Implement call_tool_sync helper in src/gateway/tools.py
- [ ] T035 [US2] Implement semantic search via x_amz_bedrock_agentcore_search in src/gateway/tools.py
- [ ] T036 [US2] Implement graceful error handling for tool unavailability in src/gateway/tools.py
- [ ] T037 [US2] Add Observability tracing for tool invocations in src/gateway/tools.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - agents have Agent Cards and can access tools via Gateway

---

## Phase 5: User Story 3 - Specify Enhanced Agent Inputs and Outputs (Priority: P2)

**Goal**: Agent developers can specify detailed input/output schemas beyond Agent Card defaults for semantic type validation

**Independent Test**: Define agents with enhanced input/output schemas as custom metadata, verify orchestrator can query and validate compatibility

### Tests for User Story 3

- [ ] T038 [P] [US3] Contract test for custom metadata schema in tests/contract/test_metadata_schema.py
- [ ] T039 [P] [US3] Unit test for metadata models in tests/unit/test_metadata_models.py
- [ ] T040 [P] [US3] Unit test for semantic validation in tests/unit/test_validation.py

### Implementation for User Story 3

- [ ] T041 [P] [US3] Create InputSchema Pydantic model in src/metadata/models.py
- [ ] T042 [P] [US3] Create OutputSchema Pydantic model in src/metadata/models.py
- [ ] T043 [US3] Create CustomAgentMetadata Pydantic model in src/metadata/models.py
- [ ] T044 [US3] Implement DynamoDB storage layer for metadata in src/metadata/storage.py
- [ ] T045 [US3] Implement put_metadata operation in src/metadata/storage.py
- [ ] T046 [US3] Implement get_metadata operation in src/metadata/storage.py
- [ ] T047 [US3] Implement semantic type compatibility matrix in src/metadata/validation.py
- [ ] T048 [US3] Implement validate_input_compatibility function in src/metadata/validation.py
- [ ] T049 [US3] Implement validate_output_compatibility function in src/metadata/validation.py

**Checkpoint**: At this point, User Story 3 is complete - agents can have enhanced input/output schemas with semantic validation

---

## Phase 6: User Story 4 - Declare Consultation Requirements (Priority: P2)

**Goal**: Agent developers can declare which other agents must be consulted during task execution for cross-functional collaboration

**Independent Test**: Define agent with consultation requirements, simulate execution, verify orchestrator blocks completion when required A2A consultations missing

### Tests for User Story 4

- [ ] T050 [P] [US4] Unit test for consultation rules in tests/unit/test_consultation_rules.py
- [ ] T051 [P] [US4] Integration test for consultation enforcement in tests/integration/test_consultation_enforcement.py

### Implementation for User Story 4

- [ ] T052 [P] [US4] Create ConsultationPhase enum in src/consultation/rules.py
- [ ] T053 [P] [US4] Create ConsultationCondition Pydantic model in src/consultation/rules.py
- [ ] T054 [US4] Create ConsultationRequirement Pydantic model in src/consultation/rules.py
- [ ] T055 [US4] Create ConsultationOutcome Pydantic model in src/consultation/rules.py
- [ ] T056 [US4] Implement ConsultationEngine class in src/consultation/enforcement.py
- [ ] T057 [US4] Implement get_requirements method in src/consultation/enforcement.py
- [ ] T058 [US4] Implement evaluate_condition method for conditional consultations in src/consultation/enforcement.py
- [ ] T059 [US4] Implement query_observability_traces for A2A consultation verification in src/consultation/enforcement.py
- [ ] T060 [US4] Implement validate_task_completion that blocks on missing consultations in src/consultation/enforcement.py
- [ ] T061 [US4] Add consultation requirements to CustomAgentMetadata storage in src/metadata/storage.py

**Checkpoint**: At this point, User Story 4 is complete - consultation requirements are enforced before task completion

---

## Phase 7: User Story 5 - Query Agent Capabilities for Task Assignment (Priority: P3)

**Goal**: Orchestrator can discover agents via A2A and query custom metadata for intelligent task assignment with full validation

**Independent Test**: Deploy multiple agents with Agent Cards and custom metadata, verify orchestrator discovers via `/.well-known/agent-card.json`, filters by skills, matches to task requirements

### Tests for User Story 5

- [ ] T062 [P] [US5] Unit test for agent discovery in tests/unit/test_discovery.py
- [ ] T063 [P] [US5] Unit test for agent query interface in tests/unit/test_query.py
- [ ] T064 [P] [US5] Integration test for registry API in tests/integration/test_registry_api.py

### Implementation for User Story 5

- [ ] T065 [US5] Implement A2A Agent Card discovery in src/registry/discovery.py
- [ ] T066 [US5] Implement fetch_agent_card from /.well-known/agent-card.json in src/registry/discovery.py
- [ ] T067 [US5] Implement discover_all_agents via A2A protocol in src/registry/discovery.py
- [ ] T068 [US5] Create AgentRegistry class in src/registry/query.py
- [ ] T069 [US5] Implement find_by_skill method in src/registry/query.py
- [ ] T070 [US5] Implement find_by_input_compatibility method in src/registry/query.py
- [ ] T071 [US5] Implement check_compatibility method in src/registry/query.py
- [ ] T072 [US5] Implement get_consultation_requirements method in src/registry/query.py
- [ ] T073 [US5] Create AgentStatus Pydantic model in src/registry/models.py
- [ ] T074 [US5] Implement status tracking storage in src/registry/status.py
- [ ] T075 [US5] Create API stack with Lambda + API Gateway in infrastructure/cdk/stacks/api_stack.py
- [ ] T076 [US5] Implement listAgents Lambda handler in src/registry/handlers.py
- [ ] T077 [US5] Implement getAgent Lambda handler in src/registry/handlers.py
- [ ] T078 [US5] Implement updateAgentMetadata Lambda handler in src/registry/handlers.py
- [ ] T079 [US5] Implement getConsultationRequirements Lambda handler in src/registry/handlers.py
- [ ] T080 [US5] Implement checkCompatibility Lambda handler in src/registry/handlers.py
- [ ] T081 [US5] Implement findCompatibleAgents Lambda handler in src/registry/handlers.py
- [ ] T082 [US5] Implement getAgentStatus Lambda handler in src/registry/handlers.py
- [ ] T083 [US5] Implement updateAgentStatus Lambda handler in src/registry/handlers.py

**Checkpoint**: All user stories should now be independently functional - full agent framework with discovery, tools, metadata, consultation, and registry API

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T084 [P] Create GitHub Actions CI workflow in .github/workflows/ci.yml
- [ ] T085 [P] Add test coverage configuration with 80% minimum threshold
- [ ] T086 [P] Create integration test stack naming and cleanup in infrastructure/cdk/
- [ ] T087 Run quickstart.md validation to verify all examples work
- [ ] T088 Code cleanup and ensure consistent error handling across modules
- [ ] T089 Security review of DynamoDB access patterns and IAM roles
- [ ] T090 Performance validation: Agent Card discovery < 500ms for 100 agents

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase
- **User Story 2 (Phase 4)**: Depends on Foundational phase; integrates with US1 for agent context
- **User Story 3 (Phase 5)**: Depends on Foundational phase; extends US1 with custom metadata
- **User Story 4 (Phase 6)**: Depends on US3 (uses CustomAgentMetadata storage)
- **User Story 5 (Phase 7)**: Depends on US1, US3, US4 (queries all agent data)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 2 (Foundational)
        │
        ├──────────┬──────────┐
        ▼          ▼          │
      US1 ←──── US2          │
   (Agent Card)  (Gateway)    │
        │                     │
        ▼                     │
      US3 ◄───────────────────┘
   (Metadata)
        │
        ▼
      US4
 (Consultation)
        │
        ▼
      US5
   (Registry)
```

- **US1 & US2**: Both P1 priority, can run in parallel after Foundational
- **US3**: P2 priority, depends on US1 for agent context
- **US4**: P2 priority, depends on US3 for metadata storage
- **US5**: P3 priority, depends on US1, US3, US4 for full agent data

### Parallel Opportunities

#### Phase 1 (Setup)
```bash
# All setup tasks can run in parallel:
Task: T003 "Configure ruff for linting"
Task: T004 "Create .env.example"
Task: T005 "Create pytest configuration"
```

#### Phase 2 (Foundational)
```bash
# These can run in parallel:
Task: T007 "Create ValidationRule model"
Task: T009 "Create DynamoDB metadata stack"
Task: T010 "Create DynamoDB status table"
Task: T012 "Create logging configuration"
```

#### Phase 3 (User Story 1 - Agent Cards)
```bash
# Tests can run in parallel:
Task: T013 "Contract test for Agent Card schema"
Task: T014 "Unit test for base agent class"

# Models can run in parallel:
Task: T015 "Create Skill Pydantic model"
Task: T016 "Create AgentCard Pydantic model"

# All 9 agent manifests can run in parallel:
Task: T019 "Orchestrator manifest"
Task: T020 "Requirements manifest"
Task: T021 "Design manifest"
Task: T022 "Architect manifest"
Task: T023 "Development manifest"
Task: T024 "Testing manifest"
Task: T025 "Security manifest"
Task: T026 "Review manifest"
Task: T027 "UI/UX manifest"
```

#### Phase 5 (User Story 3 - Metadata)
```bash
# Schema models can run in parallel:
Task: T041 "Create InputSchema model"
Task: T042 "Create OutputSchema model"
```

#### Phase 7 (User Story 5 - Registry)
```bash
# Tests can run in parallel:
Task: T062 "Unit test for discovery"
Task: T063 "Unit test for query"
Task: T064 "Integration test for registry API"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Agent Cards)
4. Complete Phase 4: User Story 2 (Gateway Tools)
5. **STOP and VALIDATE**: Test that agents can be deployed and access tools
6. Deploy/demo if ready - core agent infrastructure working

### Incremental Delivery

1. **Setup + Foundational** → Foundation ready
2. **Add US1 + US2** → Agents with Agent Cards can access tools (MVP!)
3. **Add US3** → Enhanced input/output validation
4. **Add US4** → Consultation enforcement
5. **Add US5** → Full registry API for orchestrator
6. Each increment adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers after Foundational phase:
- Developer A: User Story 1 (Agent Cards) + User Story 2 (Gateway)
- Developer B: User Story 3 (Metadata) → User Story 4 (Consultation)
- Developer C: Infrastructure (CDK stacks) + CI/CD (GitHub Actions)

After US1-4 complete, all can work on US5 (Registry API handlers).

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group per Constitution Principle VIII
- Stop at any checkpoint to validate story independently
- Performance target: Agent Card discovery < 500ms for 100 agents (SC-007)
