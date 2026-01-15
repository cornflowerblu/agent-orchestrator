# Feature Specification: Agent Framework

**Feature Branch**: `001-agent-framework`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Base agent structure with capability manifests, tool registry, inputs/outputs declaration, and consultation requirements"

## AgentCore Integration Summary

**THIS FEATURE USES AGENTCORE NATIVE CAPABILITIES** with custom extensions for consultation requirements.

### What AgentCore Provides (We Use)

- **Agent Cards (A2A Protocol)** - Native capability declaration mechanism via `skills` array, served at `/.well-known/agent-card.json`
- **Runtime** - Serverless agent deployment using `@app.entrypoint` decorator
- **Gateway** - Tool/MCP server integration, agents discover tools via `mcp_client.list_tools_sync()`
- **Agent Discovery** - A2A protocol enables agents to discover each other via Agent Cards
- **Version Management** - `version` field in Agent Card tracks agent definition changes

### What We Build (Custom Extensions)

- **Enhanced Input/Output Validation** - Beyond basic `defaultInputModes`/`defaultOutputModes`, we add typed schemas and compatibility checking
- **Consultation Requirements** - Not native to AgentCore; we build a consultation protocol layer declaring mandatory/optional agent consultations
- **Agent Registry Query Interface** - Orchestrator-facing API to query agents by skills, input compatibility, and consultation requirements

### Architecture

```
Agent Definition (Agent Card JSON)
  ↓
AgentCore Runtime Deployment (@app.entrypoint)
  ↓
Discovery via /.well-known/agent-card.json
  ↓
Tools accessed via Gateway (MCP protocol)
  ↓
Custom: Consultation Rules Engine validates required consultations
```

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Agent with Agent Card (Priority: P1)

As a platform administrator, I need to define a new agent with an Agent Card (A2A protocol) so that the orchestrator can discover the agent's skills and route work appropriately.

**Why this priority**: This is the foundational capability that enables all other agent functionality. Agent Cards are the native AgentCore mechanism for declaring what an agent can do. Without Agent Card definitions, agents cannot be discovered or assigned work. This is the core building block of the entire orchestration platform.

**Independent Test**: Can be fully tested by deploying an agent with an Agent Card, querying `/.well-known/agent-card.json`, and verifying the agent's skills are discoverable via the A2A protocol.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Agent Card Definition and Deployment
  As a platform administrator
  I want to define agents with Agent Cards (A2A protocol)
  So that the orchestrator can discover what each agent can do

  Scenario: Deploy a new agent with Agent Card
    Given I am a platform administrator
    And I have a valid Agent Card JSON with name "Requirements Agent"
    And the Agent Card includes skills "requirements-gathering" and "user-story-creation"
    When I deploy the agent to AgentCore Runtime using @app.entrypoint
    Then the agent should be deployed and running
    And the Agent Card should be served at /.well-known/agent-card.json
    And the orchestrator should be able to discover the agent via A2A protocol

  Scenario: Define agent with detailed skill descriptions
    Given I am a platform administrator
    When I create an Agent Card with skill "code-review"
    And the skill has description "Reviews code for quality, security, and best practices"
    And the skill has tags ["quality", "security"]
    Then the skill description should be included in the Agent Card
    And the description should be retrievable when querying /.well-known/agent-card.json

  Scenario: Prevent duplicate agent names
    Given an agent named "Design Agent" already exists in AgentCore Runtime
    When I attempt to deploy another agent named "Design Agent"
    Then the deployment should be rejected
    And an error indicating duplicate agent name should be returned

  Scenario: Update existing agent skills with versioning
    Given an agent named "Testing Agent" v1.0.0 exists with skill "unit-testing"
    When I update the Agent Card to add skill "integration-testing"
    And I increment the version to v1.1.0
    Then the agent should expose both "unit-testing" and "integration-testing" skills
    And the Agent Card version field should show "1.1.0"
    And new task assignments should use the updated agent version
```

---

### User Story 2 - Access Tools via Gateway (Priority: P1)

As an agent developer, I need my agent to discover and access tools through AgentCore Gateway so that my agent can interact with external APIs, Lambda functions, and MCP servers to perform work.

**Why this priority**: Tools are the mechanisms through which agents perform work. Gateway provides the native AgentCore mechanism for tool discovery and access. Without Gateway integration, agents cannot execute their skills. This is equally critical as Agent Cards since skills without tools are not actionable.

**Independent Test**: Can be fully tested by deploying a Gateway with tool definitions, having an agent call `mcp_client.list_tools_sync()`, and verifying the agent can discover and invoke tools through the Gateway.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Agent Tool Access via Gateway
  As an agent developer
  I want my agent to discover and access tools via AgentCore Gateway
  So that my agent can interact with external systems and perform work

  Scenario: Discover available tools from Gateway
    Given the "Development Agent" is deployed in AgentCore Runtime
    And a Gateway is configured with tools "code-editor", "file-system", and "terminal"
    When the Development Agent calls mcp_client.list_tools_sync()
    Then the agent should receive a list containing all three tools
    And each tool should include its name, description, and input schema

  Scenario: Invoke a tool through Gateway
    Given the "Testing Agent" has discovered tool "test-runner" via Gateway
    And the tool has input schema requiring "test_path" and "framework"
    When the Testing Agent invokes the tool with valid parameters
    Then the Gateway should execute the tool
    And the agent should receive the tool's response
    And the invocation should be traced in AgentCore Observability

  Scenario: Access MCP server via Gateway
    Given the "Security Agent" needs to use "vulnerability-scanner-mcp"
    And the MCP server is registered with the Gateway
    When the Security Agent calls mcp_client.list_tools_sync()
    Then the tools from "vulnerability-scanner-mcp" should be listed
    And the agent can invoke MCP tools through the Gateway

  Scenario: Handle tool unavailability gracefully
    Given the "Architect Agent" attempts to invoke tool "diagram-generator"
    And the tool "diagram-generator" is not registered with the Gateway
    When the agent calls the tool
    Then the Gateway should return an error indicating tool not found
    And the agent should receive an error response
    And the error should be logged in AgentCore Observability

  Scenario: Use Gateway semantic search for tool discovery
    Given a Gateway has multiple tools registered
    And the "Review Agent" needs a tool for "analyzing code quality"
    When the agent uses x_amz_bedrock_agentcore_search with query "code analysis"
    Then the Gateway should return semantically relevant tools
    And the agent can select and invoke the most appropriate tool
```

---

### User Story 3 - Specify Enhanced Agent Inputs and Outputs (Priority: P2)

As an agent developer, I need to specify detailed input/output schemas beyond Agent Card `defaultInputModes`/`defaultOutputModes` so that the orchestrator can validate data flow between agents with type safety and ensure task prerequisites are met.

**Why this priority**: While Agent Cards provide basic input/output modes (text, image, audio), multi-agent workflows need detailed type validation (e.g., "technical-specification" document vs. "user-requirements" document). This builds on Agent Card definitions (P1) but adds the semantic typing needed for complex orchestration.

**Independent Test**: Can be fully tested by defining agents with enhanced input/output schemas, storing these as custom metadata alongside Agent Cards, and verifying the orchestrator can query and validate compatibility between agents.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Enhanced Agent Input and Output Validation
  As an agent developer
  I want to specify detailed input/output schemas as custom metadata
  So that the orchestrator can validate data flow between agents with semantic types

  Scenario: Declare required inputs with semantic types
    Given I am defining the "Development Agent"
    And the Agent Card has defaultInputModes: ["text"]
    When I add custom metadata declaring required input "technical-specification" of type "document"
    And I add custom metadata declaring required input "architecture-decision-records" of type "collection"
    Then both inputs should be stored as custom validation rules
    And the orchestrator should block task assignments missing these semantic types

  Scenario: Declare optional inputs with semantic types
    Given I am defining the "Testing Agent"
    And the Agent Card has defaultInputModes: ["text"]
    When I add custom metadata declaring required input "source-code" of type "artifact"
    And I add custom metadata declaring optional input "test-data-samples" of type "collection"
    Then the orchestrator should allow tasks with or without "test-data-samples"
    And the orchestrator must reject tasks without "source-code"

  Scenario: Declare agent outputs with semantic types
    Given I am defining the "Requirements Agent"
    And the Agent Card has defaultOutputModes: ["text"]
    When I add custom metadata declaring output "user-stories" of type "collection"
    And I add custom metadata declaring output "acceptance-criteria" of type "document"
    Then the outputs should be stored with the agent's custom metadata
    And the orchestrator should know what semantic artifacts to expect

  Scenario: Validate semantic compatibility between agents
    Given "Architect Agent" has custom output metadata "system-design" of type "document"
    And "Development Agent" has custom input metadata "technical-specification" of type "document"
    When the orchestrator checks semantic compatibility
    Then "system-design" should be compatible with "technical-specification"
    And the agents should be linkable in a workflow

  Scenario: Reject task with incompatible semantic types
    Given "Development Agent" requires input "technical-specification" of type "document"
    And a task provides input "user-feedback" of type "comment"
    When the orchestrator validates the task assignment
    Then the assignment should be rejected
    And an error indicating semantic type mismatch should be returned
```

---

### User Story 4 - Declare Consultation Requirements (Priority: P2)

As an agent developer, I need to declare which other agents my agent must consult during task execution (stored as custom metadata) so that critical reviews and validations are not bypassed and cross-functional collaboration is enforced.

**Why this priority**: Consultation requirements ensure quality gates and cross-functional input. This is a **custom feature** built on top of AgentCore's A2A protocol for agent-to-agent communication. While A2A enables agents to call each other, consultation enforcement (who MUST consult whom, and when) requires custom business logic. This builds on Agent Card definitions (P1) but can be tested independently.

**Independent Test**: Can be fully tested by defining an agent with consultation requirements (custom metadata), simulating agent execution, and verifying that the orchestrator blocks task completion when required consultations via A2A are missing.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Agent Consultation Requirements (Custom on A2A)
  As an agent developer
  I want to declare which agents must be consulted via A2A protocol
  So that required reviews and validations are enforced by the orchestrator

  Scenario: Declare mandatory consultation requirement in custom metadata
    Given I am defining the "Development Agent"
    When I add custom metadata declaring mandatory consultation with "Security Agent" for phase "pre-completion"
    Then the consultation requirement should be stored in the agent's custom metadata
    And the orchestrator should enforce this requirement before task completion
    And consultations must occur via A2A JSON-RPC protocol

  Scenario: Declare optional consultation recommendation in custom metadata
    Given I am defining the "Design Agent"
    When I add custom metadata declaring recommended consultation with "UI/UX Agent" for phase "design-review"
    Then the recommendation should be stored with the agent's custom metadata
    And the orchestrator should suggest but not enforce the consultation

  Scenario: Declare conditional consultation requirement
    Given I am defining the "Architect Agent"
    When I add custom metadata declaring consultation with "Security Agent" when "handling-sensitive-data" is true
    Then the consultation should only be required when the condition is met
    And the orchestrator should evaluate the condition at runtime
    And tasks without sensitive data should skip the consultation

  Scenario: Block task completion without required A2A consultation
    Given "Development Agent" has custom metadata requiring consultation with "Review Agent"
    And the Development Agent is executing a task
    And the agent has not made an A2A call to "Review Agent"
    When the task attempts to complete
    Then the orchestrator should block completion
    And an error indicating missing required A2A consultation should be returned

  Scenario: Record and validate consultation outcome via A2A
    Given "Development Agent" is executing a task
    And custom metadata requires consultation with "Security Agent"
    When "Development Agent" sends A2A message to "Security Agent"
    And "Security Agent" responds via A2A with outcome "approved"
    Then the orchestrator should record the consultation in AgentCore Observability
    And the task should be allowed to proceed to completion
```

---

### User Story 5 - Query Agent Capabilities for Task Assignment (Priority: P3)

As the orchestrator, I need to discover agents via A2A Agent Cards and query custom metadata for enhanced input/output types and consultation requirements so that I can intelligently assign tasks to the most appropriate agent and validate all prerequisites.

**Why this priority**: This story represents the orchestrator's consumption of all the data defined in P1 and P2 stories. It depends on Agent Card deployment (P1) and custom metadata (P2) being complete. This provides the integration point that makes the framework useful for intelligent task assignment.

**Independent Test**: Can be fully tested by deploying multiple agents with Agent Cards and custom metadata, then verifying the orchestrator can discover agents via `/.well-known/agent-card.json`, query custom metadata, filter by skills, and match agents to task requirements.

**Acceptance Scenarios** (Gherkin format REQUIRED):

```gherkin
Feature: Orchestrator Agent Discovery and Query
  As the orchestrator
  I want to discover agents via A2A and query custom metadata
  So that I can assign tasks to appropriate agents with full validation

  Scenario: Discover all agents via A2A Agent Cards
    Given multiple agents are deployed in AgentCore Runtime
    And each agent serves an Agent Card at /.well-known/agent-card.json
    When the orchestrator performs A2A discovery
    Then a list of all agents should be returned
    And each Agent Card should include name, version, URL, and skills array

  Scenario: Query agents by skill
    Given "Requirements Agent" has Agent Card with skill "user-story-creation"
    And "Design Agent" has Agent Card with skill "interface-design"
    And "Development Agent" has Agent Card with skill "code-implementation"
    When the orchestrator queries for agents with skill "user-story-creation"
    Then only "Requirements Agent" should be returned

  Scenario: Discover tools via Gateway (not agent-specific)
    Given "Development Agent" needs to know available tools
    When the orchestrator queries the Gateway for available tools
    Then the Gateway should return all registered tools
    And tools are shared across agents, not agent-specific

  Scenario: Find compatible agents using custom input metadata
    Given a task has available input "user-requirements" of type "document"
    And "Requirements Agent" has custom metadata accepting input "user-requirements" of type "document"
    And "Development Agent" has custom metadata requiring input "technical-specification" of type "document"
    When the orchestrator queries for agents compatible with task inputs
    Then "Requirements Agent" should be returned as compatible
    And "Development Agent" should not be returned

  Scenario: Query agent consultation requirements from custom metadata
    Given "Development Agent" has custom metadata requiring consultations with "Security Agent" and "Review Agent"
    When the orchestrator queries consultation requirements for "Development Agent"
    Then the response should list "Security Agent" and "Review Agent"
    And each consultation should indicate its phase and whether it is mandatory

  Scenario: Validate complete task assignment with all metadata
    Given a task requiring skill "code-implementation"
    And the task provides input "technical-specification" of type "document"
    And "Development Agent" has Agent Card skill "code-implementation"
    And "Development Agent" has custom metadata accepting input "technical-specification"
    When the orchestrator validates task assignment to "Development Agent"
    Then the assignment should be validated as feasible
    And any required consultations from custom metadata should be included in the assignment plan
```

---

### Edge Cases

- What happens when an Agent Card is deployed with no skills?
  - The AgentCore Runtime should accept deployment (skills array can be empty), but the orchestrator should not assign tasks to agents with empty skills
- What happens when a Gateway tool becomes unavailable during task execution?
  - The agent should receive a tool invocation error from Gateway, handle gracefully, and optionally escalate to the orchestrator
- How does the system handle circular consultation requirements in custom metadata?
  - The orchestrator should detect cycles when validating consultation rules and reject configurations that would create deadlocks
- What happens when an agent is updated (new version) while tasks are in progress?
  - In-progress tasks should continue with the previous Agent Card version (using the same Runtime URL); new tasks should discover and use the updated Agent Card version
- How does the system handle conflicting input/output semantic types in custom metadata?
  - The orchestrator should use a type compatibility matrix (e.g., "document" types are broadly compatible) and support explicit type mappings defined by administrators

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST deploy agents to AgentCore Runtime with unique names using `@app.entrypoint`
- **FR-002**: System MUST generate Agent Cards (A2A protocol) with skills array served at `/.well-known/agent-card.json`
- **FR-003**: System MUST support updating Agent Card versions while maintaining version history in the `version` field
- **FR-004**: System MUST enable agents to discover tools via Gateway using `mcp_client.list_tools_sync()`
- **FR-005**: System MUST enable agents to access MCP servers registered with Gateway
- **FR-006**: System MUST handle Gateway tool invocation errors gracefully with appropriate error responses
- **FR-007**: System MUST store enhanced input/output schemas as custom metadata alongside Agent Cards
- **FR-008**: System MUST provide semantic type validation (beyond Agent Card `defaultInputModes`/`defaultOutputModes`)
- **FR-009**: Orchestrator MUST validate input/output semantic type compatibility between agents using custom metadata
- **FR-010**: System MUST store consultation requirements (mandatory/optional/conditional) as custom metadata
- **FR-011**: System MUST support conditional consultation requirements based on task attributes evaluated at runtime
- **FR-012**: Orchestrator MUST block task completion when mandatory A2A consultations are not recorded in Observability
- **FR-013**: System MUST provide A2A-based agent discovery for the orchestrator via Agent Card queries
- **FR-014**: Orchestrator MUST support filtering agents by Agent Card skills and custom metadata (inputs, consultations)
- **FR-015**: System MUST track agent status (available, busy, unavailable) for scheduling decisions via custom monitoring
- **FR-016**: AgentCore Runtime MUST reject agent deployment with duplicate names
- **FR-017**: Orchestrator SHOULD warn when an Agent Card has an empty skills array (but AgentCore allows it)

### Key Entities

- **Agent**: An AI agent deployed to AgentCore Runtime via `@app.entrypoint`, identified by unique name, serving an Agent Card at `/.well-known/agent-card.json`
- **Agent Card**: A2A protocol JSON document containing agent name, version, URL, protocolVersion, capabilities, defaultInputModes, defaultOutputModes, and skills array
- **Skill**: A named ability within an Agent Card's skills array, with id, name, description, and tags, used for task matching by the orchestrator
- **Gateway**: AgentCore service that converts APIs/Lambda functions to MCP-compatible tools, providing tool discovery and invocation for all agents
- **Custom Agent Metadata**: Platform-specific extensions to Agent Cards including enhanced input/output schemas and consultation requirements, stored separately from Agent Cards
- **Input Schema (Custom)**: Enhanced semantic type declaration (e.g., "technical-specification" of type "document") stored as custom metadata for orchestrator validation
- **Output Schema (Custom)**: Enhanced semantic type declaration for agent artifacts, stored as custom metadata for downstream compatibility validation
- **Consultation Requirement (Custom)**: Declaration of which agents must be consulted via A2A protocol, with phase, mandatory/optional flag, and conditional triggers, stored as custom metadata
- **Agent Card Version**: Semantic version in Agent Card `version` field tracking agent definition changes over time

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Platform administrators can deploy a new agent with Agent Card to AgentCore Runtime in under 5 minutes
- **SC-002**: All 9 platform agents (Orchestrator, Requirements, Design, UI/UX, Architect, Development, Testing, Security, Review) can be fully deployed with Agent Cards and custom metadata
- **SC-003**: The orchestrator can discover agents via A2A and match them to tasks with 100% accuracy based on Agent Card skills and custom metadata
- **SC-004**: Gateway tool errors are handled gracefully with agents receiving appropriate error responses 100% of the time
- **SC-005**: Custom metadata semantic type validation catches 100% of incompatible agent pairings before workflow execution
- **SC-006**: Mandatory A2A consultation requirements block task completion with 100% enforcement rate when consultations are missing from Observability traces
- **SC-007**: Agent Card discovery via `/.well-known/agent-card.json` returns results in under 500 milliseconds for up to 100 deployed agents
- **SC-008**: Agent Card version updates do not disrupt in-progress tasks using the previous version's Runtime URL
