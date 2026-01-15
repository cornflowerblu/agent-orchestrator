# Feature Specification: Objective Escalation System

**Feature Branch**: `003-escalation-system`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Objective escalation triggers for human oversight based on measurable criteria"

---

## AgentCore Integration Summary

**THIS IS A FULLY CUSTOM FEATURE** built on top of AWS Bedrock AgentCore primitives. AgentCore does not provide native escalation capabilities.

### What AgentCore Provides (We Use)

- **Observability Service** - OpenTelemetry traces showing agent actions, errors, performance metrics, and tool usage
- **EventBridge Integration** - Publish escalation events to trigger downstream workflows
- **Memory Service** - Store escalation history and context across sessions
- **Lambda/Runtime** - Execute escalation detection logic and trigger evaluation
- **A2A Protocol** - Send human responses back to agents

### What We Build (Custom)

- **Escalation Detection Service** - Lambda/service that monitors AgentCore Observability traces
- **Trigger Evaluation Engine** - Evaluates objective criteria from constitution (error counts, progress signals, file changes)
- **Metrics Aggregation** - Collects and analyzes agent activity from Observability traces
- **Human Notification System** - Integrates with SNS/SQS/EventBridge for human alerts
- **Escalation Dashboard** - UI for viewing/responding to escalations (see Feature 008)
- **Override/Pause Controls** - Custom control plane for human intervention
- **Agent Control API** - Send pause/resume/override commands to agents

### Implementation Approach

1. **Monitor**: Subscribe to AgentCore Observability traces for all agent activities
2. **Collect**: Extract metrics (error types, file modifications, test results, tool calls) from traces
3. **Detect**: Analyze aggregated metrics to identify trigger conditions (repeated errors, no progress, scope drift)
4. **Publish**: Send escalation events to EventBridge when triggers fire
5. **Notify**: Route escalation events to human operators via dashboard, email, or SNS
6. **Respond**: Humans interact via Oversight Dashboard (Feature 008) to approve/redirect/cancel
7. **Resume**: Agent receives human response via A2A protocol or direct API call

### Data Flow

```
AgentCore Observability Traces
         ↓
Escalation Detection Service (Lambda)
         ↓
Trigger Evaluation Engine
         ↓
EventBridge (escalation event)
         ↓
    ┌───┴───┐
    ↓       ↓
SNS/Email  Oversight Dashboard (Feature 008)
              ↓
         Human Response
              ↓
         A2A Protocol
              ↓
         Agent Resumes
```

---

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  All escalation triggers are OBJECTIVE and MEASURABLE - NO fuzzy confidence scores allowed.
  Triggers are based on constitution-defined thresholds:
  - Verification Failures: same_error_repeated: 3, total_verification_attempts: 10
  - Progress Stalls: no_file_changes_after_attempts: 5, no_test_improvement_after: 3
  - Scope Signals: files_modified_exceeds: 20, spec_deviation_detected: true
  - External Blockers: missing_dependency, permission_denied, api_unavailable
-->

### User Story 1 - Repeated Error Escalation (Priority: P1)

As a development team, when the escalation detection service observes an agent encountering the same error 3 times in succession (via AgentCore Observability traces), the system automatically escalates to a human operator so that persistent issues are addressed before wasting further compute resources.

**Why this priority**: This is the most common failure mode - agents stuck in loops attempting the same failing approach. Detecting and escalating repeated errors prevents resource waste and ensures humans can provide guidance when agents are clearly stuck.

**Independent Test**: Can be fully tested by simulating an agent that produces the same error 3 times and verifying that the escalation detection service monitors the Observability traces, detects the pattern, publishes an escalation event to EventBridge, and generates a human notification with all relevant context. Delivers immediate value by preventing infinite retry loops.

**AgentCore Components Used**: Observability (error traces), EventBridge (escalation events), Memory (escalation history)

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Repeated Error Detection and Escalation
  Agents must escalate when the same error occurs 3 times consecutively

  Scenario: Agent escalates after third identical error
    Given an agent is executing a task
    And the escalation detection service is monitoring AgentCore Observability traces
    And the agent has encountered error "TypeError: undefined is not a function" 2 times previously
    When the agent encounters the same error "TypeError: undefined is not a function" again
    Then the escalation detection service identifies the repeated error pattern
    And the system creates an escalation record
    And publishes an escalation event to EventBridge
    And the escalation includes the error message repeated 3 times
    And the escalation includes the file and line number where each error occurred from traces
    And the escalation includes the agent's attempted remediation actions from traces
    And the human operator is notified of the escalation via dashboard/SNS

  Scenario: Different errors do not trigger repeated error escalation
    Given an agent is executing a task
    And the agent has encountered error "TypeError: undefined is not a function" 2 times
    When the agent encounters a different error "ReferenceError: x is not defined"
    Then no escalation is created for repeated errors
    And the repeated error counter resets to 1 for the new error type

  Scenario: Error count resets after successful operation
    Given an agent has encountered the same error 2 times
    When the agent successfully completes an operation without error
    Then the repeated error counter resets to 0
    And no escalation is created
```

---

### User Story 2 - Progress Stall Escalation (Priority: P1)

As a development team, when the escalation detection service observes an agent making 5 consecutive attempts without modifying any files (via Observability traces), or 3 test runs without improvement in pass rate, the system escalates to human oversight so that stalled work is identified and redirected.

**Why this priority**: Agents that appear busy but make no measurable progress waste resources and delay project completion. Objective progress metrics (file changes, test improvements) extracted from Observability traces provide clear, measurable indicators of productive work.

**Independent Test**: Can be fully tested by simulating an agent that makes 5 tool calls without any file modifications, verifying the escalation detection service monitors traces, detects no file change events, and triggers escalation. Delivers value by ensuring all agent activity produces measurable outcomes.

**AgentCore Components Used**: Observability (tool calls, file modification traces), EventBridge (escalation events), Memory (progress history)

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Progress Stall Detection and Escalation
  Agents must escalate when no measurable progress is made

  Scenario: Agent escalates after 5 attempts with no file changes
    Given an agent is executing a task
    And the agent has made 4 attempts without modifying any files
    When the agent completes a 5th attempt without modifying any files
    Then the system creates an escalation record
    And the escalation includes a summary of all 5 attempted actions
    And the escalation includes the current task context
    And the human operator is notified of the progress stall

  Scenario: File modification resets the no-progress counter
    Given an agent has made 4 attempts without modifying any files
    When the agent modifies a file
    Then the no-progress counter resets to 0
    And no escalation is created

  Scenario: Agent escalates after 3 test runs with no improvement
    Given an agent is working on fixing failing tests
    And the test pass rate was 60% at the start
    And the agent has run tests 2 times with pass rates of 60% and 60%
    When the agent runs tests a 3rd time with pass rate still at 60%
    Then the system creates an escalation record
    And the escalation indicates "no test improvement after 3 attempts"
    And the escalation includes the test pass rate history
    And the human operator is notified

  Scenario: Test improvement resets the stall counter
    Given an agent has run tests 2 times with no improvement
    And the pass rate was 60% for both runs
    When the agent runs tests and the pass rate increases to 70%
    Then the test stall counter resets to 0
    And no escalation is created
```

---

### User Story 3 - Scope Drift Escalation (Priority: P2)

As a development team, when the escalation detection service observes an agent modifying more than 20 files (via Observability traces) or deviating from the specification, the system escalates so that humans can verify the changes are appropriate and aligned with project goals.

**Why this priority**: Scope creep is a significant risk with autonomous agents. Objective thresholds for file modification counts (tracked via Observability) and spec deviation detection ensure humans maintain oversight of large or unexpected changes.

**Independent Test**: Can be fully tested by simulating an agent that modifies a 21st file, verifying the escalation detection service counts file modifications in traces, and triggers escalation with a list of all modified files. Delivers value by preventing runaway changes.

**AgentCore Components Used**: Observability (file modification traces, tool usage), EventBridge (escalation events), Memory (modification history)

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Scope Drift Detection and Escalation
  Agents must escalate when work scope exceeds defined limits

  Scenario: Agent escalates when modifying more than 20 files
    Given an agent is executing a task
    And the agent has already modified 20 files in this task
    When the agent attempts to modify a 21st file
    Then the system creates an escalation record before the modification
    And the escalation includes a list of all 20 previously modified files
    And the escalation includes the proposed 21st file modification
    And the escalation requests human approval to proceed
    And the agent pauses until human response is received

  Scenario: Agent escalates when spec deviation is detected
    Given an agent is executing a task with a defined specification
    And the specification defines work on the "authentication" module
    When the agent attempts to modify files in the "payment" module
    Then the system detects spec deviation
    And the system creates an escalation record
    And the escalation includes the original spec scope
    And the escalation includes the attempted out-of-scope modification
    And the agent pauses until human response is received

  Scenario: Files within scope do not trigger escalation
    Given an agent has modified 15 files
    And all modifications are within the specified scope
    When the agent modifies a 16th file within scope
    Then no escalation is created
    And the agent continues working
```

---

### User Story 4 - External Blocker Escalation (Priority: P2)

As a development team, when the escalation detection service observes an agent encountering external blockers (missing dependencies, permission denials, or unavailable APIs via error traces), the system immediately escalates so that humans can resolve infrastructure or access issues.

**Why this priority**: External blockers are outside the agent's ability to resolve. Immediate escalation (detected via Observability error traces) prevents wasted retry attempts and ensures humans are notified of infrastructure issues that may affect multiple agents or tasks.

**Independent Test**: Can be fully tested by simulating a permission denied error, verifying the escalation detection service identifies the external blocker pattern in traces, and triggers immediate escalation with the specific resource and required permissions. Delivers value by fast-tracking resolution of infrastructure issues.

**AgentCore Components Used**: Observability (error traces, external API failures), EventBridge (high-priority escalation events), Memory (blocker history)

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: External Blocker Detection and Escalation
  Agents must escalate immediately when encountering external blockers

  Scenario: Agent escalates on missing dependency
    Given an agent is executing a task
    When the agent encounters a missing dependency "lodash@4.17.21"
    Then the system immediately creates an escalation record
    And the escalation type is "external_blocker"
    And the escalation includes the dependency name and version
    And the escalation includes the file requiring the dependency
    And the human operator is notified with high priority

  Scenario: Agent escalates on permission denied
    Given an agent is executing a task
    When the agent receives a permission denied error for resource "/etc/secrets/api-key"
    Then the system immediately creates an escalation record
    And the escalation type is "external_blocker"
    And the escalation includes the resource path
    And the escalation includes the attempted operation (read/write/execute)
    And the human operator is notified with high priority

  Scenario: Agent escalates on API unavailability
    Given an agent is executing a task
    When the agent receives HTTP 503 from external API "api.github.com"
    Then the system immediately creates an escalation record
    And the escalation type is "external_blocker"
    And the escalation includes the API endpoint
    And the escalation includes the HTTP status code
    And the escalation includes the timestamp of the failure
    And the human operator is notified with high priority

  Scenario: Transient network error does not immediately escalate
    Given an agent is executing a task
    When the agent receives a transient network timeout
    And the agent successfully retries the operation
    Then no escalation is created
```

---

### User Story 5 - Human Escalation Response (Priority: P3)

As a human operator, I can view escalation details in the Oversight Dashboard (Feature 008), provide guidance, override agent decisions, or redirect agent work so that I maintain effective control over agent behavior.

**Why this priority**: After escalation detection (P1/P2), humans need tools to respond effectively. This completes the escalation loop but depends on escalation detection being implemented first. Human responses are sent back to agents via A2A protocol or custom Agent Control API.

**Independent Test**: Can be fully tested by creating an escalation record, verifying a human can view it in the dashboard, respond with guidance, and the agent receives the response via A2A protocol and acknowledges it. Delivers value by closing the human-in-the-loop feedback cycle.

**AgentCore Components Used**: A2A Protocol (send human responses to agents), Memory (store escalation responses), EventBridge (response notifications)

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Human Escalation Response and Agent Control
  Humans must be able to respond to escalations and control agent behavior

  Scenario: Human views escalation details
    Given an escalation has been created for agent "agent-123"
    When the human operator views the escalation
    Then the operator sees the escalation type
    And the operator sees the trigger criteria that caused the escalation
    And the operator sees the agent's current task and context
    And the operator sees the agent's recent action history
    And the operator sees available response options

  Scenario: Human provides guidance to resume agent work
    Given an escalation is pending for agent "agent-123"
    And the escalation type is "repeated_error"
    When the human operator provides guidance "Try using async/await instead of callbacks"
    Then the guidance is recorded in the escalation record
    And the agent receives the guidance
    And the agent acknowledges receipt of guidance
    And the agent resumes work with the new guidance
    And the escalation status changes to "resolved"

  Scenario: Human overrides agent approach
    Given an escalation is pending for agent "agent-123"
    When the human operator selects "override" and specifies new approach "Abandon current approach, use library X instead"
    Then the override is recorded in the escalation record
    And the agent stops current work
    And the agent begins work with the specified approach
    And the escalation status changes to "resolved_with_override"

  Scenario: Human terminates agent task
    Given an escalation is pending for agent "agent-123"
    When the human operator selects "terminate task"
    Then the termination is recorded in the escalation record
    And the agent stops all work on the current task
    And the task status changes to "terminated_by_human"
    And the escalation status changes to "resolved_with_termination"

  Scenario: Human approves scope expansion
    Given an escalation is pending for scope exceeding 20 files
    When the human operator approves the expanded scope
    And specifies new limit of 30 files
    Then the approval is recorded
    And the agent resumes work with the new file limit
    And the escalation status changes to "resolved_with_approval"
```

---

### Edge Cases

- What happens when multiple escalation triggers fire simultaneously (e.g., repeated error AND no progress)?
  - System creates a single escalation with all applicable triggers listed
- How does the system handle escalation when human operators are unavailable?
  - Agent pauses work and retries notification at configured intervals
  - Escalation remains pending until acknowledged
- What happens if an agent is terminated mid-escalation?
  - Escalation record is preserved with status "agent_terminated"
- How are escalation thresholds reset when a task is reassigned to a different agent?
  - Counters reset to 0 for the new agent; previous agent's escalation history is preserved
- What happens if human guidance is ambiguous or conflicting?
  - Agent may create a follow-up escalation requesting clarification

## Requirements *(mandatory)*

### Functional Requirements

**Custom Monitoring & Detection (Built by Us)**

- **FR-001**: Escalation Detection Service MUST subscribe to AgentCore Observability traces for all agents
- **FR-002**: Metrics Aggregation MUST extract error types, file modifications, test results, and tool calls from traces
- **FR-003**: Trigger Evaluation Engine MUST track consecutive identical errors per agent and create an escalation when count reaches 3
- **FR-004**: Trigger Evaluation Engine MUST track total verification attempts per task and create an escalation when count reaches 10
- **FR-005**: Trigger Evaluation Engine MUST track file modification activity from traces and create an escalation after 5 consecutive attempts with no file changes
- **FR-006**: Trigger Evaluation Engine MUST track test pass rates from traces and create an escalation after 3 consecutive test runs with no improvement
- **FR-007**: Trigger Evaluation Engine MUST track files modified per task from traces and create an escalation when count exceeds 20
- **FR-008**: Trigger Evaluation Engine MUST detect when agent modifications (from traces) deviate from the task specification scope
- **FR-009**: Trigger Evaluation Engine MUST immediately escalate on external blocker events detected in error traces (missing_dependency, permission_denied, api_unavailable)

**Custom Control & Notification (Built by Us)**

- **FR-010**: Agent Control API MUST pause agent work when scope-related escalations are created, pending human approval
- **FR-011**: Human Notification System MUST publish escalation events to EventBridge when triggers fire
- **FR-012**: Human Notification System MUST route escalation events to SNS, dashboard, or email based on escalation type and priority
- **FR-013**: Oversight Dashboard (Feature 008) MUST provide human operators with full escalation context including trigger criteria, agent history from traces, and current task state
- **FR-014**: Oversight Dashboard MUST allow human operators to provide guidance, override, terminate, or approve expanded scope
- **FR-015**: Agent Control API MUST deliver human responses to agents via A2A protocol and confirm acknowledgment

**Storage & State Management (Using AgentCore Memory + Custom)**

- **FR-016**: System MUST persist all escalation records in AgentCore Memory including trigger data, human responses, and resolution status
- **FR-017**: Metrics Aggregation MUST reset relevant counters when agents make measurable progress (file changes, test improvements, successful operations detected in traces)
- **FR-018**: System MUST NOT use subjective confidence scores or fuzzy metrics for escalation decisions - only objective trace data

### Key Entities

**Custom Components**

- **EscalationDetectionService**: Lambda/service that subscribes to AgentCore Observability traces and monitors agent activities
- **MetricsAggregator**: Component that extracts structured metrics (errors, file changes, test results) from Observability traces
- **TriggerEvaluationEngine**: Component that evaluates objective criteria against constitution thresholds and determines when to escalate
- **AgentControlAPI**: Custom API that sends pause/resume/override commands to agents via A2A protocol
- **HumanNotificationSystem**: Component that publishes escalation events to EventBridge and routes to SNS/dashboard/email

**Data Models**

- **Escalation**: A record of an escalation event including type, trigger criteria, agent context (from traces), human response, and resolution status (stored in AgentCore Memory)
- **EscalationTrigger**: The specific objective criteria that caused the escalation (error_count, attempt_count, file_count, blocker_type) extracted from traces
- **EscalationResponse**: Human operator's response including response_type (guidance, override, terminate, approve), content, and timestamp
- **AgentMetrics**: Running counters for each agent including consecutive_same_errors, attempts_without_file_change, test_runs_without_improvement, files_modified_count (aggregated from traces)
- **ObservabilityTrace**: AgentCore trace data including tool calls, errors, file modifications, test results (provided by AgentCore)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Escalation Detection Service successfully subscribes to and processes 100% of AgentCore Observability traces
- **SC-002**: 100% of repeated errors (3+ identical) result in escalation within 1 second of detection from traces
- **SC-003**: 100% of progress stalls (5 attempts without file changes) result in escalation within 1 second of detection from traces
- **SC-004**: 100% of external blockers result in immediate escalation (within 1 second of detection from error traces)
- **SC-005**: 100% of scope limit breaches (>20 files) result in escalation before the 21st file modification (detected from traces)
- **SC-006**: Human operators receive escalation notifications via EventBridge/SNS within 5 seconds of escalation creation
- **SC-007**: Human responses are delivered to agents via A2A protocol within 2 seconds of submission
- **SC-008**: All escalation records include complete context extracted from traces as defined in FR-013
- **SC-009**: Zero escalations are created based on subjective or non-measurable criteria - only objective trace data
- **SC-010**: Agent work is paused within 1 second of scope-related escalation creation via Agent Control API
- **SC-011**: Escalation resolution rate: 95% of escalations are resolved within 1 hour of creation
- **SC-012**: All escalation records are successfully persisted in AgentCore Memory with 100% durability

---

## Technical Architecture *(optional)*

### System Components

This feature consists entirely of **custom-built components** that integrate with AgentCore primitives:

**1. Escalation Detection Service (Lambda)**
- Subscribes to AgentCore Observability trace stream
- Processes traces in real-time (event-driven or streaming)
- Invokes Metrics Aggregator and Trigger Evaluation Engine
- Publishes escalation events to EventBridge

**2. Metrics Aggregator (Lambda/Service)**
- Extracts structured data from Observability traces:
  - Error types, messages, stack traces
  - Tool calls and file modification events
  - Test execution results and pass rates
  - API calls and external service interactions
- Maintains per-agent running counters (in-memory or DynamoDB)
- Detects patterns (consecutive errors, lack of progress)

**3. Trigger Evaluation Engine (Lambda/Service)**
- Compares aggregated metrics against constitution-defined thresholds
- Evaluates trigger conditions:
  - `same_error_repeated >= 3`
  - `no_file_changes_after_attempts >= 5`
  - `no_test_improvement_after >= 3`
  - `files_modified_exceeds >= 20`
  - `spec_deviation_detected == true`
  - External blockers detected in error traces
- Creates escalation records
- Publishes escalation events to EventBridge

**4. Human Notification System (EventBridge + SNS/SQS)**
- EventBridge rules route escalation events by type/priority
- SNS topics for high-priority escalations (external blockers)
- SQS queues for dashboard polling or email notifications
- Integrates with Oversight Dashboard (Feature 008)

**5. Agent Control API (API Gateway + Lambda)**
- Receives human responses from Oversight Dashboard
- Sends pause/resume/override commands to agents
- Uses A2A protocol to communicate with agents
- Confirms acknowledgment and updates escalation status in Memory

**6. Escalation Storage (AgentCore Memory)**
- Stores escalation records with full trace context
- Stores human responses and resolution status
- Enables querying escalation history for patterns
- Provides cross-session persistence

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Trace Monitoring | Lambda + EventBridge | Event-driven, scalable, low-latency |
| Metrics Aggregation | Lambda + DynamoDB (optional) | Stateless with optional state for counters |
| Trigger Evaluation | Lambda | Stateless, fast evaluation logic |
| Notifications | EventBridge + SNS/SQS | Native AWS integration, reliable delivery |
| Agent Control | API Gateway + Lambda + A2A | RESTful API for dashboard, A2A for agents |
| Storage | AgentCore Memory | Managed, cross-session persistence |
| Dashboard | See Feature 008 | React + AppSync + GraphQL |

### Integration Points with AgentCore

1. **Observability Traces** (Input): Subscribe to trace stream via EventBridge or Kinesis
2. **Memory Service** (Storage): Store/retrieve escalation records via AgentCore Memory API
3. **A2A Protocol** (Output): Send human responses to agents via Agent Card endpoints
4. **EventBridge** (Output): Publish escalation events for downstream processing

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentCore Platform                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Agents (Runtime)                                            │   │
│  │    - Tool calls                                              │   │
│  │    - File modifications                                      │   │
│  │    - Error handling                                          │   │
│  └───────────────────┬──────────────────────────────────────────┘   │
│                      │                                               │
│                      ▼                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Observability Service (OpenTelemetry Traces)               │   │
│  └───────────────────┬──────────────────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────────────────┘
                         │
                         ▼ (EventBridge or streaming)
┌─────────────────────────────────────────────────────────────────────┐
│                    Custom Escalation System                         │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Escalation Detection Service (Lambda)                        │ │
│  │    - Subscribes to Observability traces                       │ │
│  │    - Invokes Metrics Aggregator                               │ │
│  └────────────────────┬───────────────────────────────────────────┘ │
│                       │                                              │
│                       ▼                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Metrics Aggregator (Lambda)                                  │ │
│  │    - Extracts errors, file changes, test results              │ │
│  │    - Maintains per-agent counters                             │ │
│  └────────────────────┬───────────────────────────────────────────┘ │
│                       │                                              │
│                       ▼                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Trigger Evaluation Engine (Lambda)                           │ │
│  │    - Evaluates constitution thresholds                        │ │
│  │    - Creates escalation records                               │ │
│  │    - Publishes to EventBridge                                 │ │
│  └────────────────────┬───────────────────────────────────────────┘ │
│                       │                                              │
└───────────────────────┼──────────────────────────────────────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │    EventBridge          │
          │  (Escalation Events)    │
          └─────────────┬───────────┘
                        │
            ┌───────────┴────────────┐
            │                        │
            ▼                        ▼
┌─────────────────────┐  ┌──────────────────────────────┐
│   SNS/SQS/Email    │  │  Oversight Dashboard         │
│  (Notifications)    │  │  (Feature 008)               │
└─────────────────────┘  │    - View escalations        │
                         │    - Provide human response  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │  Agent Control API           │
                         │  (API Gateway + Lambda)      │
                         │    - Send via A2A protocol   │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentCore Platform                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Memory Service                                              │   │
│  │    - Store escalation records                                │   │
│  │    - Store human responses                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  A2A Protocol                                                │   │
│  │    - Deliver human responses to agents                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Event-Driven vs. Polling**: Use event-driven architecture with EventBridge to minimize latency
2. **Stateless Services**: Keep Lambda functions stateless; use DynamoDB or Memory for counters
3. **Trace Processing**: Process traces incrementally rather than batch to enable real-time detection
4. **Decoupled Notification**: Decouple detection from notification via EventBridge for flexibility
5. **A2A Protocol**: Leverage AgentCore's native A2A protocol for agent communication rather than building custom transport

### Dependencies

- **Feature 008 (Oversight Dashboard)**: Required for human response UI
- **Constitution (Principle VI)**: Defines escalation thresholds and objective criteria
- **AgentCore Observability**: Must emit comprehensive traces including errors, tool calls, file modifications
- **AgentCore Memory**: Must support storing structured escalation records with query capabilities
- **AgentCore A2A**: Agents must implement A2A protocol to receive human responses

---
