<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0
Bump rationale: Added Principle VIII - Conventional Commits (MINOR)

Added sections:
- Principle VIII: Conventional Commits with Logical Chunks

Templates requiring updates:
- ✅ .specify/templates/spec-template.md (Gherkin enforcement added in v1.0.0)

Follow-up TODOs: None
-->

# Agent Orchestrator Platform Constitution

## Core Principles

### I. Spec-Driven Development

All features MUST follow the GitHub Spec-Kit workflow:

- Specification created and approved before implementation begins
- Implementation plan derived from specification
- Tasks generated from plan with clear dependencies
- No code written without an approved spec

**Rationale**: Ensures alignment between requirements and implementation, prevents scope creep, and provides traceability.

### II. Gherkin User Stories (NON-NEGOTIABLE)

All user stories and acceptance criteria MUST use Gherkin syntax:

- `Feature:` describes the capability
- `Scenario:` describes specific test cases
- `Given` establishes preconditions
- `When` describes the action
- `Then` describes expected outcomes
- `And` / `But` for additional conditions

Example:

```gherkin
Feature: Agent task assignment
  Scenario: Orchestrator assigns task to capable agent
    Given a development task requiring Python expertise
    And the development agent has Python capability declared
    When the orchestrator receives the task
    Then the task is assigned to the development agent
    And the agent receives the full task context
```

**Rationale**: Gherkin provides unambiguous, testable acceptance criteria that can be automated.

### III. Verification-First Completion

Agents MUST NOT mark work as complete until ALL verification checks pass:

- Linting passes with zero errors
- All tests pass
- Build succeeds
- Security scans report no critical/high issues
- Output validates against spec requirements

**Rationale**: Ensures quality gates are objective and measurable, not self-assessed.

### IV. Objective Escalation Triggers

Agents MUST escalate to human oversight based on measurable criteria only:

**Verification Failures**:

- Same error repeated 3 times in a row
- Total verification attempts exceed 10

**Progress Stalls**:

- No file changes after 5 attempts
- No test improvement after 3 iterations

**Scope Signals**:

- Files modified exceeds 20 for a single task
- Output deviates from spec requirements

**External Blockers**:

- Missing dependency
- Permission denied
- External API unavailable

Agents MUST NOT use fuzzy confidence scores or subjective assessments for escalation decisions.

**Rationale**: Eliminates unreliable self-reported confidence; all triggers are programmatically detectable.

### V. Inter-Agent Consultation Protocol

Agents MUST consult other agents before finalizing decisions in their domain:

**Architect Agent**:

- MUST consult Security Agent before finalizing infrastructure decisions
- MUST consult Design Agent when architecture impacts system design

**Development Agent**:

- MUST consult Review Agent before marking code complete
- MUST consult Testing Agent for test coverage verification

**All Agents**:

- MAY consult other agents for feasibility checks
- MUST document consultation outcomes in task artifacts

**Rationale**: Ensures cross-functional review and prevents siloed decision-making.

### VI. Autonomous with Human Oversight

Agents operate in autonomous loops with configurable checkpoints:

- Checkpoint every 3 iterations minimum
- Human approval gates at workflow stage boundaries
- Override mechanism available at all times
- All agent decisions logged for audit

Humans retain authority to:

- Pause any agent at any time
- Redirect agent work
- Cancel tasks
- Override agent decisions

**Rationale**: Balances efficiency of autonomous execution with human control and accountability.

### VII. Bedrock AgentCore Foundation

The platform MUST be built on AWS Bedrock AgentCore as its foundation:

**Core AgentCore Services (REQUIRED)**:

- **Runtime** - Serverless agent execution with multi-agent workload support
- **Memory** - Short-term (conversation) and long-term (cross-session) persistence with shared memory across agents
- **Gateway** - MCP server integration and tool exposure (JIRA, Slack, GitHub, custom APIs)
- **Observability** - Built-in tracing, debugging, and CloudWatch integration

**Supporting AgentCore Services (USE AS NEEDED)**:

- **Code Interpreter** - Sandboxed execution for Python/JavaScript/TypeScript
- **Browser** - Web interaction via Playwright/BrowserUse for UI testing agents
- **Policy** - Cedar policies for governance and tool access control
- **Evaluations** - Automated agent quality assessment

**Supplementary AWS Services**:

- S3 for artifact storage (specs, generated code, design docs)
- EventBridge for workflow triggers and external integrations
- Cognito for human user authentication (oversight dashboard)
- CloudWatch for metrics and alarms beyond AgentCore observability

Custom infrastructure outside AgentCore requires explicit justification documenting why AgentCore capabilities are insufficient.

**Rationale**: AgentCore provides purpose-built multi-agent infrastructure with native MCP support, shared memory, and observability - avoiding custom orchestration complexity.

### VIII. Conventional Commits with Logical Chunks

All commits MUST follow the Conventional Commits specification and be organized into logical chunks:

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

Agents MUST NOT create monolithic commits. Even when generating many files, commits MUST be broken down by logical accomplishment:

- One commit per model/entity created
- One commit per service implemented
- One commit per API endpoint added
- One commit per test suite added
- Separate commits for config vs implementation

**Examples**:

```
# GOOD - Logical chunks
feat(agent): add orchestrator agent capability manifest
feat(agent): add development agent capability manifest
feat(models): create workflow state machine entity
feat(api): implement task assignment endpoint
test(api): add contract tests for task assignment

# BAD - Monolithic
feat: add all agent files and configurations
```

**Commit Frequency**:

- Commit after each logical unit of work completes
- Commit before switching to a different task type
- Commit before consultation with another agent
- Never batch unrelated changes into a single commit

**Rationale**: Logical commits enable precise code review, easier rollbacks, clear git history, and traceability from commits back to spec requirements.

## Agent Collaboration Requirements

### Agent Capability Declaration

Every agent MUST declare:

- Capabilities (what it can do)
- Required inputs (what it needs)
- Outputs produced (what it delivers)
- Tools available (CLI, APIs, MCP servers, file operations)
- Consultation requirements (who it must consult)

### Communication Protocol

Agents communicate via AgentCore primitives:

- **Shared Memory** - AgentCore Memory for cross-agent context and state
- **Gateway Tools** - MCP servers exposed through AgentCore Gateway for inter-agent calls
- **S3 Artifacts** - Design docs, specs, and generated code for handoffs
- **EventBridge** - Async notifications and workflow triggers

### Failure Investigation

When an agent fails, it MUST:

1. Capture full context at failure point
2. Attempt root cause analysis
3. Search retrospective store for similar failures
4. Apply learned remediation if available
5. Document outcome regardless of success
6. Escalate to human if unresolved after protocol exhaustion

## Development Workflow

### Feature Development Flow

1. **Specification** (`/speckit.specify`) - Create feature spec with Gherkin acceptance criteria
2. **Planning** (`/speckit.plan`) - Generate implementation plan
3. **Tasks** (`/speckit.tasks`) - Generate actionable task list
4. **Implementation** (`/speckit.implement`) - Execute tasks with verification
5. **Review** - Multi-agent review (code, security, testing)

### Quality Gates

Every stage transition requires:

- Previous stage artifacts complete
- Verification checks passing
- Relevant agent consultations documented
- Human approval at designated gates

## Governance

- This constitution supersedes all other development practices for this project
- Amendments require: documented rationale, impact assessment, migration plan
- All PRs and reviews MUST verify compliance with these principles
- Complexity beyond these principles MUST be justified in writing
- Constitution violations block merges until resolved or explicitly waived by human

**Version**: 1.2.0 | **Ratified**: 2025-01-14 | **Last Amended**: 2025-01-14
