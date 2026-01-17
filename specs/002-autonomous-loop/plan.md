# Implementation Plan: Autonomous Loop Execution

**Branch**: `002-autonomous-loop` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-autonomous-loop/spec.md`

## Summary

Build an Agent Loop Framework that enables agents to implement autonomous execution loops with:
- Checkpoint management via AgentCore Memory service
- Exit condition evaluation via Gateway/Code Interpreter verification tools
- Iteration limit enforcement via AgentCore Policy (Cedar rules)
- Progress tracking via AgentCore Observability (OpenTelemetry traces)
- Human oversight dashboard querying Observability API

This is a **hybrid feature** combining agent-level implementation (Loop Framework library) with platform orchestration (monitoring and enforcement).

## Technical Context

**Language/Version**: Python 3.11+ (AgentCore SDK requirement)
**Primary Dependencies**: bedrock-agentcore SDK (Memory, Observability, Policy, Gateway, Code Interpreter), boto3, pydantic
**Storage**: AgentCore Memory (short-term for checkpoints), DynamoDB (existing from 001 for agent metadata/status)
**Testing**: pytest with moto for AWS mocking, pytest-asyncio for async tests
**Target Platform**: AWS Lambda via AgentCore Runtime, local development with moto
**Project Type**: Single project (extending existing src/ structure from 001)
**Performance Goals**:
- Loop initialization < 5 seconds (SC-001)
- Exit condition evaluation < 30 seconds per tool (SC-002)
- Checkpoint persistence < 10 seconds (SC-003)
- Dashboard query response < 2 seconds (SC-009)

**Constraints**:
- Must integrate with existing 001-agent-framework codebase
- Must use AgentCore primitives (no custom orchestration outside AgentCore)
- Cedar policies for iteration limits (not custom enforcement)

**Scale/Scope**: Support 9+ simultaneous agents (SC-007), configurable iteration limits per agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven Development | ✅ PASS | Spec created and approved before implementation |
| II. Gherkin User Stories | ✅ PASS | All 5 user stories use Gherkin syntax with Feature/Scenario/Given/When/Then |
| III. Verification-First Completion | ✅ PASS | Exit conditions explicitly require verification tools (tests, linting, builds, security scans) |
| IV. Objective Escalation Triggers | ✅ PASS | Iteration limits are measurable (Cedar Policy); no fuzzy confidence scores |
| V. Inter-Agent Consultation Protocol | ✅ PASS | Spec includes consultation documentation requirements |
| VI. Autonomous with Human Oversight | ✅ PASS | Core feature: checkpoints, iteration limits, dashboard monitoring, human override |
| VII. Bedrock AgentCore Foundation | ✅ PASS | Uses Memory, Observability, Policy, Gateway, Code Interpreter |
| VIII. Conventional Commits | ✅ PASS | Will follow commit rules during implementation |

**Gate Status**: ✅ ALL PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-autonomous-loop/
├── plan.md              # This file
├── research.md          # Phase 0 output - AgentCore integration patterns
├── data-model.md        # Phase 1 output - Loop, Checkpoint, ExitCondition entities
├── quickstart.md        # Phase 1 output - Getting started guide
├── contracts/           # Phase 1 output - API schemas
│   └── loop-framework.schema.json
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── agents/              # Existing from 001
│   └── base_agent.py    # Extend with loop framework integration
├── loop/                # NEW - Agent Loop Framework
│   ├── __init__.py
│   ├── framework.py     # LoopFramework class - main helper library
│   ├── checkpoint.py    # CheckpointManager - Memory service integration
│   ├── conditions.py    # ExitConditionEvaluator - Gateway/Code Interpreter
│   └── models.py        # LoopConfig, Checkpoint, ExitCondition dataclasses
├── orchestrator/        # NEW - Monitoring & Enforcement
│   ├── __init__.py
│   ├── monitor.py       # ObservabilityMonitor - trace watching
│   ├── policy.py        # PolicyEnforcer - Cedar rule management
│   └── alerts.py        # AlertManager - iteration limit warnings
├── dashboard/           # NEW - Progress Dashboard
│   ├── __init__.py
│   ├── queries.py       # ObservabilityQueries - trace/checkpoint queries
│   └── handlers.py      # API handlers for dashboard endpoints
├── consultation/        # Existing from 001
├── gateway/             # Existing from 001
├── metadata/            # Existing from 001
├── registry/            # Existing from 001
└── exceptions.py        # Extend with loop-specific exceptions

tests/
├── contract/            # Existing
├── integration/
│   ├── test_loop_framework.py      # NEW
│   ├── test_checkpoint_memory.py   # NEW
│   ├── test_exit_conditions.py     # NEW
│   ├── test_policy_enforcement.py  # NEW
│   └── test_dashboard_queries.py   # NEW
└── unit/
    ├── test_loop_framework.py      # NEW
    ├── test_checkpoint.py          # NEW
    ├── test_conditions.py          # NEW
    ├── test_monitor.py             # NEW
    └── test_policy.py              # NEW

infrastructure/cdk/stacks/
└── loop_stack.py        # NEW - Cedar policies, dashboard API
```

**Structure Decision**: Extends existing single-project structure from 001-agent-framework. New modules (`loop/`, `orchestrator/`, `dashboard/`) follow same patterns as existing modules (`metadata/`, `registry/`, `consultation/`).

## Complexity Tracking

> No violations to justify - design uses AgentCore primitives as required by Constitution Principle VII.

## Phase 0: Research Tasks

Based on Technical Context, the following require research:

1. **AgentCore Memory API** - How to save/load checkpoints using short-term Memory
2. **AgentCore Observability API** - How to emit custom OTEL traces and query trace history
3. **AgentCore Policy (Cedar)** - How to define and enforce iteration limit rules
4. **AgentCore Code Interpreter** - How to invoke sandboxed verification tools
5. **AgentCore Gateway** - How to discover and invoke MCP tools for exit conditions

## Phase 1: Design Deliverables

After research completion:

1. **data-model.md** - LoopConfig, Checkpoint, ExitCondition, IterationEvent entities
2. **contracts/loop-framework.schema.json** - JSON schema for checkpoint format
3. **quickstart.md** - How to implement an agent using the Loop Framework
