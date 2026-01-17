# Implementation Plan: Agent Framework

**Branch**: `001-agent-framework` | **Date**: 2026-01-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-agent-framework/spec.md`

## Summary

Build the foundational agent framework on AWS Bedrock AgentCore that enables:
1. Agent definition via A2A Agent Cards with skill declarations
2. Tool discovery and access through AgentCore Gateway
3. Custom metadata for enhanced input/output validation and consultation requirements
4. Orchestrator query interface for intelligent task assignment

Technical approach: Leverage AgentCore native capabilities (Runtime, Gateway, Agent Cards) and build custom extensions (metadata storage, consultation rules engine, registry query API) using Python with DynamoDB for custom metadata persistence.

## Technical Context

**Language/Version**: Python 3.11+ (AgentCore SDK requirement)
**Primary Dependencies**: AWS Bedrock AgentCore SDK, boto3, pydantic (validation)
**Storage**: AgentCore Memory (agent state), DynamoDB (custom metadata), S3 (artifacts)
**Testing**: pytest, moto (AWS mocking), pytest-asyncio
**Target Platform**: AWS Lambda / AgentCore Runtime (serverless)
**Project Type**: Single project (backend services with Lambda handlers)
**Performance Goals**: Agent Card discovery < 500ms for 100 agents (SC-007), deployment < 5 min (SC-001)
**Constraints**: Must use AgentCore as foundation (Constitution Principle VII), A2A protocol compliance
**Scale/Scope**: 9 platform agents, up to 100 deployed agents, custom metadata per agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Spec-Driven Development | ✅ PASS | Spec approved, requirements checklist complete |
| II. Gherkin User Stories | ✅ PASS | 5 user stories with 23 Gherkin scenarios |
| III. Verification-First | ✅ PASS (design) | Will enforce via test requirements in tasks |
| IV. Objective Escalation | ✅ PASS (design) | Feature builds escalation infrastructure |
| V. Inter-Agent Consultation | ✅ PASS | Feature implements consultation protocol |
| VI. Human Oversight | ✅ PASS (design) | Will be enforced at workflow boundaries |
| VII. AgentCore Foundation | ✅ PASS | Spec explicitly uses AgentCore Runtime, Gateway, Memory |
| VIII. Conventional Commits | ✅ PASS (implementation) | Will enforce during task execution |

**Gate Status**: PASS - Proceed to Phase 0

### Post-Phase 1 Design Re-check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Spec-Driven Development | ✅ PASS | Design artifacts (research.md, data-model.md, contracts/) derived from spec |
| II. Gherkin User Stories | ✅ PASS | Data model entities map to Gherkin scenarios |
| III. Verification-First | ✅ PASS | Test structure defined (unit/, integration/, contract/); quickstart includes verification steps |
| IV. Objective Escalation | ✅ PASS | research.md documents escalation integration points |
| V. Inter-Agent Consultation | ✅ PASS | ConsultationRequirement entity and enforcement.py in project structure |
| VI. Human Oversight | ✅ PASS | Registry API supports status monitoring; consultation outcomes auditable |
| VII. AgentCore Foundation | ✅ PASS | Design uses AgentCore Runtime, Gateway, Memory, Observability; DynamoDB only for custom extensions |
| VIII. Conventional Commits | ✅ PASS | Will enforce during implementation; structure supports logical chunks |

**Post-Design Gate Status**: ✅ PASS - Ready for `/speckit.tasks`

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-framework/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── agent-card.schema.json
│   ├── custom-metadata.schema.json
│   └── registry-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── agents/                    # Agent definitions and manifests
│   ├── __init__.py
│   ├── base_agent.py          # Base agent class with AgentCore integration
│   └── manifests/             # Agent Card JSON files
│       ├── orchestrator.json
│       ├── requirements.json
│       ├── design.json
│       ├── architect.json
│       ├── development.json
│       ├── testing.json
│       ├── security.json
│       ├── review.json
│       └── uiux.json
├── metadata/                  # Custom metadata handling
│   ├── __init__.py
│   ├── models.py              # Pydantic models for metadata
│   ├── storage.py             # DynamoDB storage layer
│   └── validation.py          # Semantic type validation
├── consultation/              # Consultation rules engine
│   ├── __init__.py
│   ├── rules.py               # Consultation rule definitions
│   └── enforcement.py         # A2A consultation enforcement
├── registry/                  # Agent registry and query API
│   ├── __init__.py
│   ├── discovery.py           # A2A Agent Card discovery
│   ├── query.py               # Query interface for orchestrator
│   └── handlers.py            # Lambda handlers for API
└── gateway/                   # Gateway tool integration
    ├── __init__.py
    └── tools.py               # Tool discovery helpers

tests/
├── unit/
│   ├── test_metadata_models.py
│   ├── test_validation.py
│   └── test_consultation_rules.py
├── integration/
│   ├── test_agent_deployment.py
│   ├── test_gateway_tools.py
│   └── test_registry_api.py
└── contract/
    ├── test_agent_card_schema.py
    └── test_metadata_schema.py

infrastructure/
├── cdk/                       # AWS CDK for infrastructure
│   ├── app.py
│   └── stacks/
│       ├── metadata_stack.py  # DynamoDB tables
│       └── api_stack.py       # API Gateway + Lambda
└── agent-cards/               # Deployed Agent Card templates

.github/
└── workflows/
    └── ci.yml                 # PR quality gate (unit, integration, coverage)
```

**Structure Decision**: Single project structure with clear module separation. Agent definitions, custom metadata, consultation rules, and registry query are separate concerns but deployed together initially. CDK manages AWS infrastructure.

## Complexity Tracking

> No constitution violations requiring justification. All complexity within normal bounds:
> - Single DynamoDB table for metadata (not multiple databases)
> - Single API for registry (not microservices)
> - Pydantic for validation (standard Python pattern)

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
