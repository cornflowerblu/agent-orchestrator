# Feature Specification: Inter-Agent Consultation Protocol

**Feature Branch**: `004-agent-consultation`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Inter-agent consultation protocol with mandatory and optional patterns"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently

  CONSTITUTION REQUIREMENT: All acceptance scenarios MUST use Gherkin syntax.
  See constitution principle II. Gherkin User Stories (NON-NEGOTIABLE).
-->

### User Story 1 - Initiating Mandatory Consultation (Priority: P1)

As an agent with a mandatory consultation requirement, I need to initiate a consultation request to the required agent so that I can proceed with my decision only after receiving the required input.

**Why this priority**: Mandatory consultations are the core compliance mechanism. Without this capability, the platform cannot enforce the constitutional requirements that Architect must consult Security Agent before infrastructure decisions, and Development Agent must consult Review Agent before marking code complete.

**Independent Test**: Can be fully tested by having an Architect agent attempt an infrastructure decision and verifying that a consultation request is automatically created and sent to the Security Agent, delivering the value of enforced compliance with consultation rules.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Mandatory Consultation Initiation
  As an agent with mandatory consultation requirements
  I need to initiate consultations with required agents
  So that I comply with platform governance rules

  Scenario: Architect initiates mandatory consultation with Security Agent
    Given the Architect agent is preparing an infrastructure decision
    And infrastructure decisions require mandatory Security Agent consultation
    When the Architect agent initiates the consultation request
    Then a consultation request is created with status "pending"
    And the Security Agent receives notification of the consultation request
    And the consultation request includes the decision context and specific questions

  Scenario: Development Agent initiates mandatory consultation with Review Agent
    Given the Development Agent has completed code implementation
    And code completion requires mandatory Review Agent consultation
    When the Development Agent initiates the consultation request
    Then a consultation request is created with status "pending"
    And the Review Agent receives notification of the consultation request
    And the Development Agent cannot mark the code as complete until consultation resolves

  Scenario: Architect initiates mandatory consultation with Design Agent
    Given the Architect agent is proposing architecture changes
    And the proposed changes impact user-facing design elements
    When the Architect agent initiates the consultation request
    Then the Design Agent receives notification of the consultation request
    And the consultation request clearly identifies which design aspects are impacted
```

---

### User Story 2 - Consulted Agent Providing Response (Priority: P2)

As a consulted agent, I need to review consultation requests and provide structured responses so that the requesting agent can incorporate my input into their decision.

**Why this priority**: Without the ability to respond to consultations, the mandatory consultation process cannot complete. This is the second half of the core consultation workflow and enables the feedback loop essential for collaborative decision-making.

**Independent Test**: Can be fully tested by presenting a Security Agent with a pending consultation request and verifying the agent can submit a structured response with approval, concerns, or rejection, delivering the value of expert input in decision-making.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Consultation Response Submission
  As a consulted agent
  I need to provide structured responses to consultation requests
  So that requesting agents receive actionable feedback

  Scenario: Security Agent approves infrastructure decision
    Given the Security Agent has received a consultation request from Architect
    And the Security Agent has reviewed the infrastructure decision details
    When the Security Agent submits an approval response
    Then the consultation status changes to "approved"
    And the Architect agent is notified of the approval
    And the response includes any security recommendations or conditions

  Scenario: Security Agent raises concerns about infrastructure decision
    Given the Security Agent has received a consultation request from Architect
    And the Security Agent identifies security concerns with the proposal
    When the Security Agent submits a response with concerns
    Then the consultation status changes to "concerns-raised"
    And the Architect agent is notified of the specific concerns
    And the Architect agent must address concerns before proceeding

  Scenario: Review Agent rejects code completion
    Given the Review Agent has received a consultation request from Development Agent
    And the Review Agent identifies issues that must be resolved
    When the Review Agent submits a rejection response
    Then the consultation status changes to "rejected"
    And the Development Agent is notified of the rejection reasons
    And the code cannot be marked complete until issues are addressed

  Scenario: Testing Agent verifies coverage requirements
    Given the Testing Agent has received a consultation request from Development Agent
    And the Development Agent is requesting coverage verification
    When the Testing Agent reviews the coverage metrics
    Then the Testing Agent responds with coverage status and any gaps identified
    And the response includes specific areas requiring additional coverage if applicable
```

---

### User Story 3 - Blocking Completion Until Mandatory Consultations Complete (Priority: P3)

As the platform, I need to enforce that agents cannot finalize decisions until all mandatory consultations are complete and resolved so that governance requirements are always met.

**Why this priority**: This enforcement mechanism ensures the consultation protocol has teeth. Without blocking, mandatory consultations become advisory-only, defeating their purpose. This is critical for compliance but depends on the consultation initiation and response capabilities being in place first.

**Independent Test**: Can be fully tested by having a Development Agent attempt to mark code complete while a Review Agent consultation is still pending, verifying the system blocks the action and displays the pending consultation, delivering the value of enforced governance compliance.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Mandatory Consultation Enforcement
  As the platform
  I need to block decision finalization until mandatory consultations complete
  So that governance requirements are consistently enforced

  Scenario: Block code completion with pending Review Agent consultation
    Given the Development Agent has initiated a mandatory Review Agent consultation
    And the consultation status is "pending"
    When the Development Agent attempts to mark the code as complete
    Then the system blocks the completion action
    And the system displays a message indicating pending mandatory consultation
    And the system shows which consultation must be resolved

  Scenario: Block infrastructure decision with unresolved Security concerns
    Given the Architect has received a "concerns-raised" response from Security Agent
    And the Architect has not yet addressed the security concerns
    When the Architect attempts to finalize the infrastructure decision
    Then the system blocks the finalization
    And the system requires the Architect to address or acknowledge all concerns
    And the system maintains audit trail of the blocking event

  Scenario: Allow completion after all mandatory consultations resolved
    Given the Development Agent has mandatory consultations with Review Agent and Testing Agent
    And the Review Agent consultation status is "approved"
    And the Testing Agent consultation status is "approved"
    When the Development Agent marks the code as complete
    Then the system allows the completion action
    And the system records that all mandatory consultations were satisfied

  Scenario: Handle consultation timeout
    Given a mandatory consultation request has been pending
    And the consultation has exceeded the configured timeout threshold
    When the system evaluates the consultation status
    Then the system escalates the consultation to appropriate stakeholders
    And the requesting agent is notified of the escalation
    And the blocking remains in effect until resolved or escalation completes
```

---

### User Story 4 - Documenting Consultation Outcomes (Priority: P4)

As an agent completing a consultation, I need to document the consultation outcome and any resulting decisions so that there is a clear record of the collaborative decision-making process.

**Why this priority**: Documentation ensures accountability and enables learning from past consultations. While the consultation can technically complete without documentation, proper records are essential for audit, dispute resolution, and process improvement.

**Independent Test**: Can be fully tested by completing a consultation and verifying that a structured outcome document is created capturing the original request, response, resolution, and any conditions or follow-up items, delivering the value of institutional memory and accountability.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Consultation Outcome Documentation
  As an agent completing a consultation
  I need to document the outcome and decisions
  So that there is a clear record of the collaborative process

  Scenario: Document approved consultation outcome
    Given a consultation between Architect and Security Agent has concluded
    And the Security Agent approved the infrastructure decision
    When the consultation is marked as resolved
    Then a consultation record is created with the original request details
    And the record includes the Security Agent response and approval
    And the record includes any conditions or recommendations from Security Agent
    And the record captures the timestamp of resolution

  Scenario: Document consultation with addressed concerns
    Given a consultation had concerns raised by the consulted agent
    And the requesting agent has addressed all concerns
    When the consultation is marked as resolved
    Then the consultation record includes the original concerns
    And the record includes how each concern was addressed
    And the record includes the final approval after concerns addressed

  Scenario: Document rejected consultation and subsequent actions
    Given a consultation was rejected by the consulted agent
    And the requesting agent has made changes based on feedback
    When a new consultation is initiated
    Then the new consultation references the previous rejected consultation
    And the record shows the lineage of consultation attempts
    And the changes made in response to rejection are documented
```

---

### User Story 5 - Viewing Consultation Audit Trail (Priority: P5)

As a platform administrator or agent, I need to view the complete audit trail of all consultations so that I can review decision-making history, identify patterns, and ensure compliance.

**Why this priority**: The audit trail enables oversight, compliance verification, and process improvement. While not required for day-to-day consultation operations, it is essential for governance, troubleshooting, and demonstrating regulatory compliance.

**Independent Test**: Can be fully tested by querying the consultation audit system for a specific agent, time period, or decision type and verifying that all relevant consultations are returned with complete details, delivering the value of transparency and accountability.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Consultation Audit Trail
  As a platform administrator or agent
  I need to view consultation history
  So that I can review decisions and ensure compliance

  Scenario: View all consultations for a specific agent
    Given consultations have occurred involving the Architect agent
    When an administrator queries consultations for the Architect agent
    Then all consultations where Architect was requester are displayed
    And all consultations where Architect was consulted are displayed
    And each consultation shows status, participants, and outcome

  Scenario: View consultations by time period
    Given multiple consultations have occurred over several days
    When an administrator queries consultations for a specific date range
    Then all consultations within that range are returned
    And consultations are sorted by date with most recent first
    And summary statistics are provided for the period

  Scenario: View consultations by decision type
    Given consultations have occurred for various decision types
    When an administrator filters consultations by "infrastructure decisions"
    Then only consultations related to infrastructure decisions are displayed
    And the filter shows how many consultations matched the criteria
    And the results can be further filtered by status or outcome

  Scenario: Export consultation audit trail
    Given an administrator needs to provide consultation records for compliance
    When the administrator requests an export of consultation records
    Then the system generates a complete export of matching consultations
    And the export includes all consultation details and outcomes
    And the export is in a format suitable for compliance reporting
```

---

### Edge Cases

- What happens when the consulted agent is unavailable or offline for an extended period?
- How does the system handle circular consultation requirements (Agent A must consult B, but B's response requires consulting A)?
- What happens when a mandatory consultation is initiated but the consulted agent role is currently unassigned?
- How does the system handle simultaneous consultations from multiple agents to the same consulted agent?
- What happens when a consulted agent needs to delegate their consultation response to another agent?
- How does the system handle consultation requests that span multiple mandatory consultation rules?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow agents to initiate consultation requests to other agents
- **FR-002**: System MUST distinguish between mandatory and optional consultation patterns
- **FR-003**: System MUST enforce that Architect agents consult Security Agent before infrastructure decisions
- **FR-004**: System MUST enforce that Architect agents consult Design Agent when architecture impacts design
- **FR-005**: System MUST enforce that Development Agent consults Review Agent before marking code complete
- **FR-006**: System MUST enforce that Development Agent consults Testing Agent for coverage verification
- **FR-007**: System MUST allow any agent to initiate optional consultations for feasibility checks
- **FR-008**: System MUST block decision finalization when mandatory consultations are pending or unresolved
- **FR-009**: System MUST allow consulted agents to respond with approval, concerns, or rejection
- **FR-010**: System MUST notify requesting agents when consultation responses are submitted
- **FR-011**: System MUST notify consulted agents when new consultation requests are received
- **FR-012**: System MUST document all consultation outcomes including request, response, and resolution
- **FR-013**: System MUST maintain an audit trail of all consultations with timestamps
- **FR-014**: System MUST provide query capabilities for consultation history by agent, time period, and decision type
- **FR-015**: System MUST handle consultation timeout scenarios with appropriate escalation
- **FR-016**: System MUST support consultation response conditions and recommendations
- **FR-017**: System MUST link related consultations when resubmission occurs after rejection

### Key Entities

- **Consultation Request**: Represents a request from one agent to another for input on a decision. Key attributes include requesting agent, consulted agent, decision context, consultation type (mandatory/optional), questions or review points, and status.
- **Consultation Response**: Represents the consulted agent's response to a request. Key attributes include response type (approved/concerns-raised/rejected), response details, conditions or recommendations, and timestamp.
- **Consultation Record**: The complete documented outcome of a consultation including request, response, resolution, and any follow-up actions. Forms the basis of the audit trail.
- **Consultation Rule**: Defines the mandatory and optional consultation patterns, including which agent roles must consult which other roles for specific decision types.
- **Consultation Status**: The current state of a consultation (pending, approved, concerns-raised, rejected, escalated, resolved).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of mandatory consultations are enforced - no agent can bypass required consultation patterns
- **SC-002**: Consultation requests receive responses within the configured timeout threshold at least 95% of the time
- **SC-003**: All consultation outcomes are documented with complete audit trail within 1 minute of resolution
- **SC-004**: Agents can initiate a consultation request in 3 steps or fewer
- **SC-005**: Consulted agents can submit a response in 3 steps or fewer
- **SC-006**: Audit trail queries return results within 5 seconds for searches spanning up to 90 days
- **SC-007**: Zero decisions are finalized without completing mandatory consultations (verified through audit)
- **SC-008**: 100% of consultation records include requesting agent, consulted agent, decision context, response, and resolution timestamp
