# Feature Specification: Inter-Agent Consultation Protocol

**Feature Branch**: `004-agent-consultation`
**Created**: 2026-01-14
**Updated**: 2026-01-14
**Status**: Draft
**Input**: User description: "Inter-agent consultation protocol with mandatory and optional patterns"

## Architecture Overview

This feature leverages **AWS Bedrock AgentCore's native A2A (Agent-to-Agent) Protocol** for communication and builds a **custom consultation rules engine** for enforcement.

**What AgentCore Provides (Native):**
- **A2A Protocol** - Agent-to-agent JSON-RPC 2.0 communication
- **Agent Discovery** - Agents find each other via Agent Cards at `/.well-known/agent-card.json`
- **Message Format** - Standardized request/response using JSON-RPC
- **Observability** - Audit trail of all A2A calls via OpenTelemetry traces

**What We Build (Custom):**
- **Consultation Rules Engine** - Defines who MUST consult whom (from constitution)
- **Enforcement Logic** - Blocks agent completion until consultations done
- **Consultation Workflow** - Request → Response → Resolution tracking
- **Consultation Status Management** - Pending, approved, concerns-raised, rejected states

### A2A Message Format

Consultations use the A2A protocol's JSON-RPC 2.0 message format:

**Consultation Request (A2A message/send):**
```json
{
  "jsonrpc": "2.0",
  "id": "consultation-req-001",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{
        "kind": "text",
        "text": "I'm proposing to use serverless architecture with Lambda and Step Functions for the new payment processing workflow. Please review from a security perspective and advise on: 1) Data encryption in transit and at rest, 2) IAM role scoping, 3) Compliance with PCI-DSS requirements."
      }],
      "messageId": "msg-uuid-001",
      "metadata": {
        "consultationType": "mandatory",
        "decisionContext": "infrastructure",
        "requestingAgent": "ArchitectAgent",
        "consultationId": "consult-uuid-001"
      }
    }
  }
}
```

**Consultation Response (A2A result with artifacts):**
```json
{
  "jsonrpc": "2.0",
  "id": "consultation-req-001",
  "result": {
    "artifacts": [{
      "artifactId": "artifact-uuid-001",
      "name": "security_consultation_response",
      "parts": [{
        "kind": "text",
        "text": "APPROVED with conditions:\n1. Use AWS KMS for encryption at rest with customer-managed keys\n2. Enable CloudTrail logging for all Lambda invocations\n3. Implement least-privilege IAM roles with resource-level permissions\n4. Use VPC endpoints for Step Functions to avoid public internet\n5. Ensure PCI-DSS compliance through AWS Artifact attestations"
      }],
      "metadata": {
        "responseType": "approved",
        "consultationId": "consult-uuid-001",
        "conditions": ["kms-encryption", "cloudtrail-logging", "least-privilege-iam", "vpc-endpoints", "pci-compliance"]
      }
    }]
  }
}
```

**Key Points:**
- Consultation requests are A2A `message/send` calls with consultation metadata
- Responses use A2A `artifacts` to return structured feedback
- Metadata carries consultation-specific fields (type, status, IDs)
- AgentCore Observability automatically captures all A2A interactions
- Our custom rules engine validates mandatory consultations are completed before allowing agent to finalize decisions

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

### User Story 1 - Initiating Mandatory Consultation via A2A Protocol (Priority: P1)

As an agent with a mandatory consultation requirement, I need to send an A2A message to the required agent so that I can proceed with my decision only after receiving the required response.

**Why this priority**: Mandatory consultations are the core compliance mechanism. Without this capability, the platform cannot enforce the constitutional requirements that Architect must consult Security Agent before infrastructure decisions, and Development Agent must consult Review Agent before marking code complete.

**Independent Test**: Can be fully tested by having an Architect agent attempt an infrastructure decision and verifying that an A2A `message/send` request is created with proper consultation metadata and sent to the Security Agent, delivering the value of enforced compliance with consultation rules.

**Technical Implementation**:
- Agent uses AgentCore's A2A client to send `message/send` to consulted agent's endpoint
- Message includes consultation metadata (type, context, consultationId)
- Custom rules engine validates mandatory consultation is initiated
- Consultation status tracked as "pending" until response received

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Mandatory Consultation Initiation
  As an agent with mandatory consultation requirements
  I need to initiate consultations with required agents
  So that I comply with platform governance rules

  Scenario: Architect initiates mandatory consultation with Security Agent via A2A
    Given the Architect agent is preparing an infrastructure decision
    And infrastructure decisions require mandatory Security Agent consultation
    And the Security Agent is discoverable via Agent Card at /.well-known/agent-card.json
    When the Architect agent sends an A2A message/send request to Security Agent
    Then the A2A message includes jsonrpc "2.0" and method "message/send"
    And the message params include consultation metadata with type "mandatory"
    And the consultation is tracked with status "pending" in the rules engine
    And the Security Agent receives the A2A request at their invocation endpoint
    And AgentCore Observability records the A2A interaction

  Scenario: Development Agent initiates mandatory consultation with Review Agent via A2A
    Given the Development Agent has completed code implementation
    And code completion requires mandatory Review Agent consultation
    And the Review Agent endpoint is known via Agent Discovery
    When the Development Agent sends an A2A message/send request to Review Agent
    Then the A2A message includes consultation metadata with consultationId
    And the consultation is tracked with status "pending" in the rules engine
    And the Development Agent cannot mark the code as complete until consultation resolves
    And the rules engine blocks completion until A2A response received

  Scenario: Architect initiates mandatory consultation with Design Agent via A2A
    Given the Architect agent is proposing architecture changes
    And the proposed changes impact user-facing design elements
    When the Architect agent sends an A2A message/send request to Design Agent
    Then the A2A message clearly identifies which design aspects are impacted
    And the message includes decisionContext metadata field
    And the Design Agent receives the A2A request
    And the consultation is tracked as "pending" in the system
```

---

### User Story 2 - Consulted Agent Providing A2A Response (Priority: P2)

As a consulted agent, I need to receive A2A consultation requests and provide structured responses via A2A artifacts so that the requesting agent can incorporate my input into their decision.

**Why this priority**: Without the ability to respond to consultations, the mandatory consultation process cannot complete. This is the second half of the core consultation workflow and enables the feedback loop essential for collaborative decision-making.

**Independent Test**: Can be fully tested by presenting a Security Agent with a pending A2A consultation request and verifying the agent can submit a structured A2A response with artifacts containing approval, concerns, or rejection, delivering the value of expert input in decision-making.

**Technical Implementation**:
- Consulted agent receives A2A `message/send` request at their invocation endpoint
- Agent processes consultation and generates response
- Response returned as A2A `result` with `artifacts` array
- Artifact metadata includes responseType (approved/concerns-raised/rejected)
- Custom rules engine updates consultation status based on response metadata

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Consultation Response Submission
  As a consulted agent
  I need to provide structured responses to consultation requests
  So that requesting agents receive actionable feedback

  Scenario: Security Agent approves infrastructure decision via A2A response
    Given the Security Agent has received an A2A message/send consultation from Architect
    And the Security Agent has reviewed the infrastructure decision details
    When the Security Agent returns an A2A result with artifacts
    Then the artifact metadata includes responseType "approved"
    And the artifact parts contain security recommendations and conditions
    And the consultation status changes to "approved" in the rules engine
    And the Architect agent receives the A2A response
    And AgentCore Observability records the response interaction

  Scenario: Security Agent raises concerns via A2A response
    Given the Security Agent has received an A2A message/send consultation from Architect
    And the Security Agent identifies security concerns with the proposal
    When the Security Agent returns an A2A result with artifacts
    Then the artifact metadata includes responseType "concerns-raised"
    And the artifact parts contain specific security concerns
    And the consultation status changes to "concerns-raised" in the rules engine
    And the Architect agent receives the A2A response with concerns
    And the rules engine requires Architect to address concerns before proceeding

  Scenario: Review Agent rejects code completion via A2A response
    Given the Review Agent has received an A2A message/send consultation from Development Agent
    And the Review Agent identifies issues that must be resolved
    When the Review Agent returns an A2A result with artifacts
    Then the artifact metadata includes responseType "rejected"
    And the artifact parts contain rejection reasons and required changes
    And the consultation status changes to "rejected" in the rules engine
    And the Development Agent receives the A2A response
    And the code cannot be marked complete until issues are addressed

  Scenario: Testing Agent verifies coverage via A2A response
    Given the Testing Agent has received an A2A message/send consultation from Development Agent
    And the Development Agent is requesting coverage verification
    When the Testing Agent reviews the coverage metrics
    Then the Testing Agent returns an A2A result with artifacts
    And the artifact parts contain coverage status and any gaps identified
    And the artifact metadata includes specific areas requiring additional coverage if applicable
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

### User Story 5 - Viewing Consultation Audit Trail via Observability (Priority: P5)

As a platform administrator or agent, I need to view the complete audit trail of all consultations via AgentCore Observability so that I can review decision-making history, identify patterns, and ensure compliance.

**Why this priority**: The audit trail enables oversight, compliance verification, and process improvement. While not required for day-to-day consultation operations, it is essential for governance, troubleshooting, and demonstrating regulatory compliance.

**Independent Test**: Can be fully tested by querying AgentCore Observability for A2A interactions filtered by consultation metadata and verifying that all relevant consultations are returned with complete details, delivering the value of transparency and accountability.

**Technical Implementation**:
- All A2A consultation messages automatically captured by AgentCore Observability
- OpenTelemetry traces include full A2A request/response payloads
- Custom query layer filters Observability data by consultation metadata
- Consultation records enriched with status from rules engine
- Export capability leverages Observability API

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Consultation Audit Trail
  As a platform administrator or agent
  I need to view consultation history
  So that I can review decisions and ensure compliance

  Scenario: View all consultations for a specific agent via Observability
    Given consultations have occurred involving the Architect agent
    When an administrator queries AgentCore Observability for Architect agent traces
    And filters by consultation metadata in A2A messages
    Then all A2A interactions where Architect was requester are displayed
    And all A2A interactions where Architect was consulted are displayed
    And each consultation shows status from rules engine, participants, and outcome
    And traces include full A2A request/response payloads

  Scenario: View consultations by time period from Observability
    Given multiple consultations have occurred over several days
    When an administrator queries Observability traces for a specific date range
    And filters by A2A method "message/send" with consultation metadata
    Then all consultation A2A interactions within that range are returned
    And consultations are sorted by timestamp with most recent first
    And summary statistics are provided for the period

  Scenario: View consultations by decision type from metadata
    Given consultations have occurred for various decision types
    When an administrator filters Observability traces by decisionContext "infrastructure"
    Then only A2A consultations related to infrastructure decisions are displayed
    And the filter shows how many consultation traces matched the criteria
    And the results can be further filtered by responseType or consultation status

  Scenario: Export consultation audit trail from Observability
    Given an administrator needs to provide consultation records for compliance
    When the administrator requests an export via Observability API
    And specifies consultation metadata filters
    Then the system generates a complete export of matching consultation traces
    And the export includes all A2A request/response details and outcomes
    And the export is in a format suitable for compliance reporting (JSON/CSV)
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

#### A2A Protocol Integration (AgentCore Native)
- **FR-001**: System MUST allow agents to send A2A `message/send` requests to other agents for consultations
- **FR-002**: System MUST use JSON-RPC 2.0 format for all consultation messages
- **FR-003**: System MUST support agent discovery via Agent Cards at `/.well-known/agent-card.json`
- **FR-004**: System MUST automatically capture all A2A consultation interactions in AgentCore Observability
- **FR-005**: System MUST include consultation metadata (type, context, consultationId) in A2A message params
- **FR-006**: System MUST return consultation responses as A2A `result` with `artifacts` array
- **FR-007**: System MUST include responseType metadata (approved/concerns-raised/rejected) in artifacts

#### Custom Consultation Rules Engine
- **FR-008**: Rules engine MUST distinguish between mandatory and optional consultation patterns from constitution
- **FR-009**: Rules engine MUST enforce that Architect agents consult Security Agent before infrastructure decisions
- **FR-010**: Rules engine MUST enforce that Architect agents consult Design Agent when architecture impacts design
- **FR-011**: Rules engine MUST enforce that Development Agent consults Review Agent before marking code complete
- **FR-012**: Rules engine MUST enforce that Development Agent consults Testing Agent for coverage verification
- **FR-013**: Rules engine MUST allow any agent to initiate optional consultations for feasibility checks
- **FR-014**: Rules engine MUST block decision finalization when mandatory consultations are pending or unresolved
- **FR-015**: Rules engine MUST track consultation status (pending, approved, concerns-raised, rejected, resolved)
- **FR-016**: Rules engine MUST validate mandatory consultations are completed before allowing agent completion

#### Consultation Workflow
- **FR-017**: System MUST handle consultation timeout scenarios with appropriate escalation
- **FR-018**: System MUST support consultation response conditions and recommendations in artifact parts
- **FR-019**: System MUST link related consultations when resubmission occurs after rejection
- **FR-020**: System MUST provide query capabilities for consultation history via Observability API filters
- **FR-021**: System MUST support export of consultation audit trail in compliance-friendly formats (JSON/CSV)

### Key Entities

#### AgentCore Native Entities
- **A2A Message (Consultation Request)**: JSON-RPC 2.0 `message/send` request from requesting agent to consulted agent. Includes consultation metadata in message params (consultationType, decisionContext, requestingAgent, consultationId).
- **A2A Response (Consultation Response)**: JSON-RPC 2.0 `result` with artifacts array. Artifact metadata includes responseType (approved/concerns-raised/rejected), consultationId, and optional conditions array. Artifact parts contain the consultation feedback text.
- **Agent Card**: JSON document at `/.well-known/agent-card.json` defining agent name, description, version, endpoint URL, and skills. Used for agent discovery in consultation workflow.
- **Observability Trace**: OpenTelemetry trace capturing full A2A request/response payload, timestamps, and consultation metadata. Automatically created by AgentCore for all A2A interactions.

#### Custom Platform Entities
- **Consultation Rule**: Defines the mandatory and optional consultation patterns from constitution, including which agent roles must consult which other roles for specific decision types. Stored in rules engine configuration.
- **Consultation Status Record**: Rules engine tracking record linking consultationId to current status (pending, approved, concerns-raised, rejected, escalated, resolved). Updated based on A2A response metadata.
- **Consultation Enforcement Policy**: Rules engine policy that blocks agent completion actions when mandatory consultations are pending or unresolved. Validates all required consultations completed before allowing finalization.

## Implementation Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOM CONSULTATION LAYER                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Consultation Rules Engine                     │  │
│  │  - Load rules from constitution                         │  │
│  │  - Track consultation status (DynamoDB)                 │  │
│  │  - Validate mandatory consultations completed           │  │
│  │  - Block agent completion if pending                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Consultation Workflow Orchestrator               │  │
│  │  - Initiate consultations (send A2A messages)           │  │
│  │  - Process responses (parse A2A artifacts)              │  │
│  │  - Update status in rules engine                        │  │
│  │  - Handle timeouts and escalations                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Audit Query Service                            │  │
│  │  - Query Observability API for consultation traces     │  │
│  │  - Filter by consultation metadata                     │  │
│  │  - Enrich with status from rules engine                │  │
│  │  - Export to JSON/CSV for compliance                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│              AWS BEDROCK AGENTCORE (NATIVE)                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                A2A Protocol Layer                        │  │
│  │  - JSON-RPC 2.0 message/send requests                   │  │
│  │  - Agent discovery via Agent Cards                      │  │
│  │  - Artifact-based responses                             │  │
│  │  - Automatic payload capture                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Agent Runtime (9 Agents)                    │  │
│  │  Architect, Security, Design, Development, Review,       │  │
│  │  Testing, Requirements, UI/UX, etc.                      │  │
│  │  Each agent exposes /.well-known/agent-card.json         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Observability Service (OpenTelemetry)          │  │
│  │  - Captures all A2A interactions automatically          │  │
│  │  - Stores full request/response payloads                │  │
│  │  - Provides query API for trace retrieval               │  │
│  │  - Timestamps and metadata indexing                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**1. Consultation Initiation:**
```
Architect Agent
  → Checks Rules Engine: "Do I need Security consultation?"
  → Rules Engine: "YES - mandatory for infrastructure decisions"
  → Architect discovers Security Agent via Agent Card
  → Architect sends A2A message/send to Security Agent endpoint
  → Rules Engine creates status record: consultationId → "pending"
  → AgentCore Observability captures A2A request
```

**2. Consultation Response:**
```
Security Agent
  → Receives A2A message/send at invocation endpoint
  → Processes infrastructure review
  → Returns A2A result with artifact (responseType: "approved")
  → Rules Engine updates status: consultationId → "approved"
  → AgentCore Observability captures A2A response
  → Architect Agent receives response
```

**3. Enforcement Check:**
```
Architect Agent
  → Attempts to finalize infrastructure decision
  → Rules Engine checks: "All mandatory consultations resolved?"
  → Rules Engine queries status records for consultationIds
  → If any "pending" or "concerns-raised": BLOCK completion
  → If all "approved": ALLOW completion
```

**4. Audit Trail Query:**
```
Administrator
  → Queries Audit Service for "infrastructure consultations last 30 days"
  → Audit Service calls Observability API with filters:
      - A2A method = "message/send"
      - metadata.decisionContext = "infrastructure"
      - timestamp range
  → Enriches traces with status from Rules Engine
  → Returns combined consultation records
```

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of mandatory consultations are enforced via rules engine - no agent can bypass required consultation patterns
- **SC-002**: 100% of consultation requests use A2A `message/send` with valid JSON-RPC 2.0 format
- **SC-003**: 100% of consultation responses use A2A `result` with artifacts containing responseType metadata
- **SC-004**: Consultation requests receive A2A responses within the configured timeout threshold at least 95% of the time
- **SC-005**: All A2A consultation interactions are automatically captured by Observability within 1 second
- **SC-006**: Agents can initiate an A2A consultation request in 3 steps or fewer (discover, construct message, send)
- **SC-007**: Consulted agents can return an A2A consultation response in 3 steps or fewer (receive, process, return artifact)
- **SC-008**: Observability audit trail queries return results within 5 seconds for searches spanning up to 90 days
- **SC-009**: Zero decisions are finalized without completing mandatory consultations (verified through Observability audit)
- **SC-010**: 100% of consultation Observability traces include requesting agent, consulted agent, decision context, responseType, and timestamps
- **SC-011**: Rules engine blocks agent completion within 100ms when pending/unresolved mandatory consultations exist
