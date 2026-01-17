# Data Model: Agent Framework

**Feature**: 001-agent-framework
**Date**: 2026-01-16

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Card (A2A)                         │
│  Native AgentCore - served at /.well-known/agent-card.json      │
├─────────────────────────────────────────────────────────────────┤
│  name, version, url, protocolVersion, capabilities,             │
│  defaultInputModes, defaultOutputModes, skills[]                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 1:1 linked by agent_name
┌──────────────────────────▼──────────────────────────────────────┐
│                    Custom Agent Metadata                        │
│  DynamoDB - our extension for orchestrator needs                │
├─────────────────────────────────────────────────────────────────┤
│  input_schemas[], output_schemas[], consultation_requirements[] │
└─────────────────────────────────────────────────────────────────┘
```

## Entities

### 1. Agent Card (Native AgentCore)

Standard A2A protocol Agent Card. We do not modify this structure.

```typescript
interface AgentCard {
  // Identity
  name: string;                    // Unique agent identifier
  description: string;             // Human-readable description
  version: string;                 // Semantic version (e.g., "1.0.0")

  // Runtime
  url: string;                     // AgentCore Runtime invocation URL
  protocolVersion: string;         // A2A protocol version (e.g., "0.3.0")
  preferredTransport: "JSONRPC";   // Always JSONRPC for A2A

  // Capabilities
  capabilities: {
    streaming: boolean;            // Whether agent supports streaming
  };

  // I/O Modes (basic types only)
  defaultInputModes: ("text" | "image" | "audio")[];
  defaultOutputModes: ("text" | "image" | "audio")[];

  // Skills
  skills: Skill[];
}

interface Skill {
  id: string;                      // Unique skill identifier
  name: string;                    // Human-readable name
  description: string;             // What this skill does
  tags: string[];                  // Categorization tags
}
```

**Storage**: AgentCore Runtime (native, served at `/.well-known/agent-card.json`)
**Identity**: `name` must be unique across all deployed agents

---

### 2. Custom Agent Metadata

Platform-specific extensions stored separately from Agent Cards.

```typescript
interface CustomAgentMetadata {
  // Primary Key
  agent_name: string;              // Links to Agent Card name

  // Enhanced I/O (beyond basic modes)
  input_schemas: InputSchema[];
  output_schemas: OutputSchema[];

  // Consultation Protocol
  consultation_requirements: ConsultationRequirement[];

  // Metadata
  version: string;                 // Should match Agent Card version
  created_at: string;              // ISO8601 timestamp
  updated_at: string;              // ISO8601 timestamp
}
```

**Storage**: DynamoDB table `AgentMetadata`
**Identity**: `agent_name` (partition key), must match an existing Agent Card

---

### 3. Input Schema

Semantic type declaration for agent inputs.

```typescript
interface InputSchema {
  name: string;                    // Input identifier (e.g., "technical-specification")
  semantic_type: SemanticType;     // Type category
  description: string;             // What this input represents
  required: boolean;               // Must be provided for task assignment
  validation_rules?: ValidationRule[];
}

type SemanticType =
  | "document"      // Structured text documents (specs, designs, etc.)
  | "artifact"      // Code, binaries, or generated files
  | "collection"    // Array of related items
  | "reference"     // Pointer to external resource
  | "comment";      // Feedback or annotations

interface ValidationRule {
  type: "format" | "length" | "pattern" | "enum";
  value: string | number | string[];
  message: string;                 // Error message if validation fails
}
```

---

### 4. Output Schema

Semantic type declaration for agent outputs.

```typescript
interface OutputSchema {
  name: string;                    // Output identifier (e.g., "user-stories")
  semantic_type: SemanticType;     // Type category
  description: string;             // What this output represents
  guaranteed: boolean;             // Always produced vs conditional
}
```

---

### 5. Consultation Requirement

Declaration of inter-agent consultation rules.

```typescript
interface ConsultationRequirement {
  id: string;                      // Unique rule identifier
  target_agent: string;            // Agent that must be consulted
  phase: ConsultationPhase;        // When consultation must occur
  mandatory: boolean;              // Required vs recommended
  condition?: ConsultationCondition;  // When rule applies (null = always)
}

type ConsultationPhase =
  | "pre-execution"    // Before starting task
  | "design-review"    // During design phase
  | "pre-completion"   // Before marking complete
  | "on-error";        // When errors occur

interface ConsultationCondition {
  attribute: string;               // Task attribute to check
  operator: "equals" | "contains" | "greater_than" | "exists";
  value: any;                      // Value to compare against
}
```

**Examples**:
- Development Agent must consult Review Agent pre-completion (mandatory, unconditional)
- Architect Agent must consult Security Agent when `handling_sensitive_data = true`
- Design Agent should consult UI/UX Agent during design-review (recommended)

---

### 6. Consultation Outcome

Recorded result of an A2A consultation (stored in AgentCore Observability).

```typescript
interface ConsultationOutcome {
  // Identity
  trace_id: string;                // AgentCore Observability trace ID

  // Participants
  source_agent: string;            // Agent that initiated consultation
  target_agent: string;            // Agent that was consulted

  // Context
  task_id: string;                 // Task being executed
  requirement_id: string;          // Which consultation rule this satisfies

  // Result
  outcome: "approved" | "rejected" | "deferred" | "error";
  feedback?: string;               // Comments from consulted agent

  // Timing
  timestamp: string;               // ISO8601 when consultation completed
}
```

**Storage**: AgentCore Observability (OpenTelemetry traces)
**Query**: Via Observability API to verify consultation compliance

---

### 7. Agent Status

Runtime status for scheduling decisions.

```typescript
interface AgentStatus {
  agent_name: string;
  status: "available" | "busy" | "unavailable" | "error";
  current_task_id?: string;        // If busy, which task
  last_heartbeat: string;          // ISO8601 timestamp
  error_message?: string;          // If error status
}
```

**Storage**: Custom monitoring (EventBridge + DynamoDB TTL or AgentCore Observability metrics)
**Note**: AgentCore doesn't provide native status tracking; this is custom implementation

---

## DynamoDB Table Design

### Table: AgentMetadata

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| agent_name | String | PK | Unique agent identifier |
| input_schemas | List | - | Array of InputSchema |
| output_schemas | List | - | Array of OutputSchema |
| consultation_requirements | List | - | Array of ConsultationRequirement |
| version | String | - | Matches Agent Card version |
| created_at | String | - | ISO8601 timestamp |
| updated_at | String | - | ISO8601 timestamp |

### GSI: SkillIndex

For querying agents by skill capability.

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| skill_id | String | PK | Skill identifier |
| agent_name | String | - | Agent with this skill |

**Note**: This GSI requires denormalization - skill_ids must be written as separate items or use a sparse GSI pattern.

### Table: AgentStatus

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| agent_name | String | PK | Unique agent identifier |
| status | String | - | Current status |
| current_task_id | String | - | Task if busy |
| last_heartbeat | String | - | ISO8601 timestamp |
| ttl | Number | - | Epoch seconds for auto-cleanup |

---

## Relationships

```
Agent Card (AgentCore)
    │
    │ 1:1 (agent_name)
    ▼
Custom Metadata (DynamoDB)
    │
    ├── 1:N Input Schemas
    ├── 1:N Output Schemas
    └── 1:N Consultation Requirements
             │
             │ validated against
             ▼
    Consultation Outcomes (Observability)
```

## State Transitions

### Agent Lifecycle

```
[Not Deployed] ──deploy──► [Available]
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
          [Busy]          [Unavailable]     [Error]
              │                │                │
              │ task_complete  │ recover        │ fix
              ▼                ▼                ▼
         [Available] ◄─────────┴────────────────┘
```

### Consultation Validation Flow

```
Task attempts completion
        │
        ▼
Query consultation requirements for agent
        │
        ▼
For each mandatory requirement:
        │
        ├── Query Observability for matching A2A trace
        │       │
        │       ├── Found with "approved" outcome → ✓ Pass
        │       ├── Found with "rejected" outcome → ✗ Fail (block)
        │       └── Not found → ✗ Fail (missing consultation)
        │
        ▼
All requirements pass? → Allow completion
Any requirement fails? → Block with specific error
```

## Validation Rules

### Agent Card

- `name`: Required, unique, alphanumeric with hyphens, max 64 chars
- `version`: Required, semantic version format (X.Y.Z)
- `skills`: At least one skill recommended (orchestrator warns if empty)

### Custom Metadata

- `agent_name`: Must match existing Agent Card
- `version`: Should match Agent Card version (warn if mismatch)
- `input_schemas[].name`: Unique within agent
- `consultation_requirements[].target_agent`: Must be valid agent name

### Semantic Type Compatibility

| Output Type | Compatible Input Types |
|-------------|----------------------|
| document | document |
| artifact | artifact, document |
| collection | collection |
| reference | reference, document |
| comment | comment, document |

Custom mappings can be defined by administrators to extend compatibility.
