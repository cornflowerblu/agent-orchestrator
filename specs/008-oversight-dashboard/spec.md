# Feature Specification: Human Oversight Dashboard

**Feature Branch**: `008-oversight-dashboard`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Human oversight dashboard with approval gates, escalations, monitoring, and override controls"

## AgentCore Integration Summary

**THIS IS A FULLY CUSTOM FEATURE** that queries AgentCore APIs and integrates with Step Functions for approvals.

### What AgentCore Provides (We Use)

- **Observability API** - Query agent execution traces, iteration counts, errors, and activity logs for real-time monitoring
- **Runtime API** - Query agent deployment status, execution state, and metadata
- **Memory API** - Query agent checkpoints and shared memory for context retrieval
- **Step Functions API** - Send task tokens (`send_task_success`/`send_task_failure`) for approval gate decisions

### What We Build (Custom Dashboard UI and APIs)

- **Dashboard Web Application** - React/Vue UI for human operators to view and act on oversight data
- **Approval Gate Interface** - UI for viewing pending approvals from Step Functions `.waitForTaskToken` states and sending decisions
- **Real-Time Monitoring Views** - Displays agent status, iteration counts, and activity logs from Observability API
- **Escalation Management** - Receives EventBridge escalation events and displays for human review
- **Override Control Panel** - Sends stop/pause commands to Step Functions executions and AgentCore Runtime
- **Audit Trail Viewer** - Queries Observability for complete history of agent decisions and human interventions

### Architecture

```
Dashboard UI (React/Vue)
  ↓
Backend API (Lambda/API Gateway)
  ├─ Queries AgentCore Observability API (agent activity, errors)
  ├─ Queries AgentCore Runtime API (agent status)
  ├─ Queries AgentCore Memory API (checkpoints, context)
  ├─ Queries Step Functions API (workflow status, pending approvals)
  └─ Sends Step Functions task tokens (approval decisions)

Approval Gates:
  Step Functions .waitForTaskToken → Lambda sends notification → Dashboard displays → Human decides → send_task_success/failure

Real-Time Updates:
  AgentCore Observability → EventBridge → Lambda → WebSocket/SSE → Dashboard

Override Controls:
  Dashboard → Backend API → Step Functions StopExecution or AgentCore Runtime stop
```

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories are PRIORITIZED as user journeys ordered by importance.
  Each user story/journey is INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Constitution Principle VI (Autonomous with Human Oversight) requires:
  - Checkpoint every 3 iterations minimum
  - Human approval gates at workflow stage boundaries
  - Override mechanism available at all times
  - All agent decisions logged for audit
-->

### User Story 1 - Viewing and Acting on Pending Approval Gates (Priority: P1)

As a human operator, I need to view all pending approval gates across active workflows so that I can review agent work at stage boundaries and make informed decisions about whether to approve continuation, request changes, or reject the work.

**Why this priority**: Approval gates are the primary mechanism for human oversight at workflow stage boundaries. Without this capability, agents cannot progress through multi-stage workflows, making this the most critical dashboard function.

**Independent Test**: Can be fully tested by creating a workflow that reaches an approval gate, then verifying the operator can view the pending approval, see relevant context, and take action. Delivers immediate value by enabling supervised agent operation.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Approval Gate Management
  As a human operator
  I need to view and act on pending approval gates
  So that I can supervise agent work at workflow stage boundaries

  Scenario: View list of pending approval gates
    Given there are active workflows with agents awaiting approval
    When I access the approval gates section of the dashboard
    Then I see a list of all pending approval gates
    And each gate displays the workflow name, agent name, current stage, and time waiting
    And the gates are sorted by urgency with oldest first

  Scenario: View approval gate details
    Given there is a pending approval gate for workflow "Customer Onboarding"
    When I select that approval gate
    Then I see the complete context including agent decisions made
    And I see the work artifacts produced during this stage
    And I see what the agent proposes to do in the next stage
    And I see any agent-provided confidence scores or risk assessments

  Scenario: Approve workflow continuation
    Given I am viewing a pending approval gate with satisfactory work
    When I approve the workflow continuation
    Then the agent is notified to proceed to the next stage
    And the approval is recorded in the audit trail with my identity and timestamp
    And the gate is removed from the pending list

  Scenario: Reject workflow stage with feedback
    Given I am viewing a pending approval gate with unsatisfactory work
    When I reject the stage and provide feedback explaining the issues
    Then the agent receives the rejection and feedback
    And the workflow status changes to indicate revision needed
    And the rejection is recorded in the audit trail with my feedback
```

---

### User Story 2 - Monitoring Agent Status and Activity (Priority: P2)

As a human operator, I need to monitor the real-time status of all active agents so that I can understand system health, identify agents that may need intervention, and maintain situational awareness of autonomous operations.

**Why this priority**: Real-time monitoring enables proactive oversight before issues escalate. While agents can operate between approval gates, operators need visibility into ongoing activity to maintain effective supervision.

**Independent Test**: Can be fully tested by running multiple agents in parallel and verifying the operator can see each agent's current status, activity, and iteration count. Delivers value by providing operational visibility.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Agent Status Monitoring
  As a human operator
  I need to monitor real-time agent status
  So that I can maintain situational awareness and identify issues early

  Scenario: View all active agents
    Given there are multiple agents running across different workflows
    When I access the agent monitoring section
    Then I see a list of all active agents
    And each agent shows its current status (running, paused, waiting, completed)
    And each agent shows its current workflow and task
    And each agent shows its iteration count since last checkpoint

  Scenario: View agent activity details
    Given agent "Research Agent" is actively running
    When I select that agent for detailed view
    Then I see the agent's current task description
    And I see a log of recent actions taken by the agent
    And I see the agent's progress toward the next checkpoint
    And I see any warnings or anomalies detected

  Scenario: Identify agents approaching checkpoint
    Given multiple agents are running with different iteration counts
    When I view the agent monitoring section
    Then agents with 2 or more iterations since last checkpoint are visually highlighted
    And I can filter to show only agents approaching the 3-iteration checkpoint requirement

  Scenario: View agent health indicators
    Given agents are running with varying performance characteristics
    When I view the agent monitoring section
    Then I see health indicators for each agent including response time and error rate
    And agents with degraded health are flagged for attention
```

---

### User Story 3 - Viewing and Responding to Escalations (Priority: P2)

As a human operator, I need to view escalated issues from agents and respond appropriately so that I can resolve situations that agents cannot handle autonomously and keep workflows progressing.

**Why this priority**: Escalations represent situations where agents have determined they need human judgment. Timely response prevents workflow stalls and ensures agents get the guidance they need.

**Independent Test**: Can be fully tested by triggering an agent escalation (e.g., exceeding confidence threshold) and verifying the operator receives notification, can view details, and can respond with guidance.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Escalation Queue Management
  As a human operator
  I need to view and respond to agent escalations
  So that I can provide guidance for situations requiring human judgment

  Scenario: View escalation queue
    Given agents have escalated multiple issues requiring human attention
    When I access the escalation queue
    Then I see all pending escalations sorted by priority and time
    And each escalation shows the escalating agent, workflow, and reason for escalation
    And escalations are categorized by type (decision needed, clarification needed, error encountered)

  Scenario: View escalation details
    Given there is an escalation about an ambiguous customer requirement
    When I select that escalation
    Then I see the full context of what the agent was attempting
    And I see what specific decision or clarification the agent needs
    And I see any options the agent has identified with tradeoffs
    And I see how long the workflow has been blocked

  Scenario: Respond to escalation with guidance
    Given I am viewing an escalation requesting a decision
    When I provide my decision and any additional guidance
    Then the agent receives my response and resumes work
    And my response is recorded in the audit trail
    And the escalation is marked as resolved

  Scenario: Escalate further to another human
    Given I am viewing an escalation that requires expertise I do not have
    When I reassign the escalation to another qualified operator
    Then the escalation moves to that operator's queue
    And the reassignment is recorded with my reason
    And I am notified when the escalation is resolved
```

---

### User Story 4 - Exercising Override Controls (Priority: P1)

As a human operator, I need to pause, redirect, or cancel agent work at any time so that I can maintain control over autonomous operations and respond to changing priorities or concerns.

**Why this priority**: Per constitution requirements, override mechanism must be available at all times. This is a safety-critical capability that ensures humans remain in control regardless of agent state.

**Independent Test**: Can be fully tested by pausing an active agent, verifying it stops, then resuming and verifying it continues. Delivers immediate value by ensuring human control.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Agent Override Controls
  As a human operator
  I need to override agent operations at any time
  So that I can maintain control and respond to changing situations

  Scenario: Pause a running agent
    Given agent "Analysis Agent" is actively processing a task
    When I issue a pause command for that agent
    Then the agent stops its current activity at the next safe point
    And the agent status changes to "paused by operator"
    And the pause action is recorded in the audit trail with my identity

  Scenario: Resume a paused agent
    Given agent "Analysis Agent" was previously paused by an operator
    When I issue a resume command
    Then the agent continues from where it was paused
    And the agent status changes back to "running"
    And the resume action is recorded in the audit trail

  Scenario: Cancel agent work entirely
    Given an agent is working on a workflow that is no longer needed
    When I cancel the agent's current task
    Then the agent stops all work on that task
    And the workflow status is updated to "cancelled"
    And any work products are preserved but marked as incomplete
    And the cancellation is recorded with my reason

  Scenario: Redirect agent to different task
    Given agent "General Agent" is working on a low-priority task
    When I redirect the agent to a higher-priority task
    Then the agent saves its current progress
    And the agent begins work on the new task
    And the original task is returned to the queue
    And the redirection is recorded in the audit trail

  Scenario: Override agent decision
    Given an agent made an automated decision I disagree with
    When I override that decision and provide my correction
    Then the agent's decision is replaced with my override
    And downstream effects of the original decision are rolled back if possible
    And the override is prominently recorded in the audit trail
```

---

### User Story 5 - Viewing Audit Trail of Agent Decisions (Priority: P3)

As a human operator, I need to view the complete audit trail of agent decisions and actions so that I can understand what happened, investigate issues, and demonstrate compliance with oversight requirements.

**Why this priority**: Per constitution requirements, all agent decisions must be logged for audit. While not blocking agent operation, this capability is essential for accountability, learning, and compliance.

**Independent Test**: Can be fully tested by running a workflow to completion, then verifying the operator can view all decisions made, actions taken, and human interventions throughout.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Audit Trail Viewing
  As a human operator
  I need to view the audit trail of agent activities
  So that I can investigate issues and ensure accountability

  Scenario: View workflow audit trail
    Given a workflow "Order Processing" has been running for several hours
    When I access the audit trail for that workflow
    Then I see a chronological log of all agent decisions
    And I see all human approvals, rejections, and overrides
    And I see timestamps and identities for all entries
    And I can see the reasoning agents provided for decisions

  Scenario: Search audit trail by criteria
    Given there is extensive audit history across multiple workflows
    When I search for all overrides made in the past week
    Then I see a filtered list of override events
    And I can further filter by operator, agent, or workflow
    And I can export the results for external review

  Scenario: View decision chain for specific outcome
    Given a workflow produced an unexpected result
    When I trace back from that outcome
    Then I see the sequence of decisions that led to it
    And I see which decisions were agent-autonomous versus human-approved
    And I see any escalations or overrides that occurred
    And I can identify the decision points that most influenced the outcome

  Scenario: Generate compliance report
    Given oversight policies require periodic compliance verification
    When I generate an audit report for a specified time period
    Then the report shows all workflows and their checkpoint compliance
    And the report shows approval gate statistics
    And the report shows override frequency and reasons
    And the report confirms the 3-iteration checkpoint requirement was met
```

---

### Edge Cases

- What happens when multiple operators attempt to act on the same approval gate simultaneously?
- How does the system handle an operator attempting to override their own previous override?
- What happens when an agent reaches a checkpoint while the dashboard is temporarily unavailable?
- How does the system behave when an escalation times out without human response?
- What happens when a paused agent's task is reassigned to another agent?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST query Step Functions API for pending `.waitForTaskToken` states and display with workflow context, agent info, and wait time
- **FR-002**: Dashboard MUST send `send_task_success` or `send_task_failure` with task token to Step Functions for approval decisions
- **FR-003**: Dashboard MUST query AgentCore Observability API for agent execution traces to display real-time status and iteration counts
- **FR-004**: Dashboard MUST highlight agents in Observability where iteration count exceeds threshold (3 iterations without checkpoint)
- **FR-005**: Dashboard MUST subscribe to EventBridge escalation events and display escalations with priority and category
- **FR-006**: Dashboard MUST allow operators to send responses via EventBridge or direct agent invocation for escalations
- **FR-007**: Dashboard MUST call Step Functions `StopExecution` API and AgentCore Runtime stop commands for control operations
- **FR-008**: Dashboard MUST record override decisions to AgentCore Memory with operator identity and justification
- **FR-009**: Dashboard MUST query AgentCore Observability for complete audit trail of agent decisions and Step Functions execution history
- **FR-010**: Dashboard MUST provide search UI that filters Observability traces by agent, timestamp, event type, and custom criteria
- **FR-011**: Dashboard backend MUST record operator identity (from Cognito) and timestamp with all human actions to Observability
- **FR-012**: Dashboard MUST generate compliance reports by querying Observability for checkpoint adherence and Step Functions for approval gate metrics

### Key Entities

- **Approval Gate (Step Functions Task Token)**: Step Functions `.waitForTaskToken` state pausing workflow execution. Dashboard queries Step Functions API for pending tokens, displays context from AgentCore Observability, and sends `send_task_success`/`send_task_failure` with operator decision
- **Escalation (EventBridge Event)**: Agent-initiated escalation sent to EventBridge with type, agent ID, reason, and required decision. Dashboard subscribes to EventBridge, displays in escalation queue, and allows operator response
- **Agent Status (Observability Trace Data)**: Real-time operational state queried from AgentCore Observability API. Contains current task, iteration count from OTEL spans, health indicators, and activity log from trace events
- **Override (Memory Record)**: Human correction of agent decision, stored in AgentCore Memory. Contains original decision from Observability, override decision, operator identity from Cognito, justification, and timestamp
- **Audit Entry (Observability Trace)**: Recorded event in AgentCore Observability or Step Functions execution history. Contains timestamp, actor (human or agent), action type, decision, and full context. Queryable via Observability API for compliance reports

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard queries Step Functions API and displays pending approval gates within 30 seconds of page load
- **SC-002**: 100% of agent decisions are recorded in AgentCore Observability with timestamps and context
- **SC-003**: Step Functions `StopExecution` API calls from dashboard respond within 5 seconds
- **SC-004**: EventBridge escalation events appear in dashboard within 10 seconds of agent emission
- **SC-005**: AgentCore Observability API queries return audit results within 5 seconds for queries spanning up to 30 days
- **SC-006**: Dashboard refreshes agent status from Observability API with no more than 10 seconds of latency
- **SC-007**: Compliance reports correctly identify 100% of checkpoint threshold violations by querying Observability traces
- **SC-008**: Operators can pause any running agent within 2 clicks (dashboard → backend → Step Functions/Runtime API)
