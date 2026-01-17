# Agent Orchestrator Platform

A multi-agent orchestration platform built on AWS Bedrock AgentCore that enables autonomous AI agents to collaborate on complex software development tasks with human oversight.

## Vision

This platform orchestrates specialized AI agents (Requirements, Design, Architecture, Development, Testing, Security, Review) to work together on software projects. Agents operate autonomously within defined guardrails, consult each other for cross-functional decisions, and escalate to humans when they hit objective blockers.

**Key principles:**
- Spec-driven development - no code without an approved specification
- Verification-first completion - agents can't mark work done until tests/builds/lints pass
- Objective escalation - no fuzzy confidence scores, only measurable triggers
- Human oversight - checkpoints, approval gates, and override controls at all times

## Architecture

Built on **AWS Bedrock AgentCore** with custom orchestration layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Custom Platform Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │  Workflow   │ │ Escalation  │ │Verification │ │  Oversight │ │
│  │   Engine    │ │   System    │ │  Pipeline   │ │  Dashboard │ │
│  │(Step Funcs) │ │  (Custom)   │ │  (Custom)   │ │  (React)   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  AWS Bedrock AgentCore                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ Runtime │ │ Memory  │ │ Gateway │ │Observa- │ │   Code    │  │
│  │         │ │         │ │  (MCP)  │ │ bility  │ │Interpreter│  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Fleet                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │
│  │Orchestrator│ │Requirements│ │  Design   │ │  UI/UX    │        │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │
│  │ Architect │ │Development│ │  Testing  │ │ Security  │        │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘        │
│  ┌───────────┐                                                   │
│  │  Review   │                                                   │
│  └───────────┘                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| **001 - Agent Framework** | Agent Cards (A2A), capability manifests, tool registry, consultation requirements | Spec complete |
| **002 - Autonomous Loop** | Checkpoint management, exit conditions, iteration limits, progress tracking | Spec complete |
| **003 - Escalation System** | Objective triggers (repeated errors, stalls, scope drift), human notification | Spec complete |
| **004 - Consultation Protocol** | Mandatory/optional inter-agent consultation via A2A, enforcement rules | Spec complete |
| **005 - Workflow Engine** | YAML DSL to Step Functions ASL, parallel execution, approval gates | Spec complete |
| **006 - Verification Pipeline** | Quality gates, regression detection, completion criteria per task type | Spec complete |
| **007 - Failure Investigation** | Context capture, pattern matching, learned remediations | Spec complete |
| **008 - Oversight Dashboard** | Real-time monitoring, approval gates, escalation queue, override controls | Spec complete |

## Agent Roles

| Agent | Responsibilities | Consults |
|-------|-----------------|----------|
| **Orchestrator** | Task assignment, workflow coordination, escalation routing | All agents |
| **Requirements** | User story creation, acceptance criteria (Gherkin) | Design |
| **Design** | System design, component architecture | Architect, UI/UX |
| **UI/UX** | Interface design, user experience | Design |
| **Architect** | Infrastructure decisions, technical architecture | Security (mandatory) |
| **Development** | Code implementation | Review (mandatory), Testing |
| **Testing** | Test coverage verification, test creation | Development |
| **Security** | Security review, vulnerability assessment | Architect |
| **Review** | Code review, quality assessment | Development |

## Constitution

The platform operates under a strict constitution (`.specify/memory/constitution.md`) that defines:

1. **Spec-Driven Development** - All features require approved specifications before implementation
2. **Gherkin User Stories** - All acceptance criteria must use Given/When/Then syntax
3. **Verification-First Completion** - Linting, tests, builds, and security scans must pass
4. **Objective Escalation Triggers** - No fuzzy confidence scores:
   - Same error repeated 3 times
   - No file changes after 5 attempts
   - No test improvement after 3 iterations
   - Files modified exceeds 20
5. **Inter-Agent Consultation** - Mandatory cross-functional reviews
6. **Human Oversight** - Checkpoints every 3 iterations, approval gates, override controls
7. **AgentCore Foundation** - Platform built on AWS Bedrock AgentCore primitives
8. **Conventional Commits** - Logical chunks with semantic commit messages

## Project Structure

```
agent-orchestrator/
├── .specify/
│   ├── memory/
│   │   └── constitution.md      # Platform governance rules
│   ├── templates/               # Spec, plan, task templates
│   └── scripts/                 # Workflow automation
├── specs/
│   ├── 001-agent-framework/
│   ├── 002-autonomous-loop/
│   ├── 003-escalation-system/
│   ├── 004-agent-consultation/
│   ├── 005-workflow-engine/
│   ├── 006-verification-pipeline/
│   ├── 007-failure-investigation/
│   └── 008-oversight-dashboard/
└── README.md
```

## Development Workflow

This project uses [GitHub Spec-Kit](https://github.com/anthropics/speckit) for spec-driven development:

1. **Specify** (`/speckit.specify`) - Create feature spec with Gherkin acceptance criteria
2. **Plan** (`/speckit.plan`) - Generate implementation plan from spec
3. **Tasks** (`/speckit.tasks`) - Generate actionable task list with dependencies
4. **Implement** (`/speckit.implement`) - Execute tasks with verification gates
5. **Review** - Multi-agent review (code, security, testing)

## Getting Started

> **Note:** This project is currently in the specification phase. Implementation has not yet begun.

### Prerequisites

- AWS Account with Bedrock AgentCore access
- Node.js 18+ or Python 3.11+
- AWS CLI configured

### Reading the Specs

Start with the constitution to understand governance:
```bash
cat .specify/memory/constitution.md
```

Then explore individual feature specs:
```bash
ls specs/
cat specs/001-agent-framework/spec.md
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Runtime | AWS Bedrock AgentCore |
| Workflow Orchestration | AWS Step Functions |
| Agent Memory | AgentCore Memory Service |
| Tool Integration | AgentCore Gateway (MCP) |
| Observability | AgentCore Observability (OpenTelemetry) |
| Verification | AgentCore Code Interpreter |
| Notifications | Amazon EventBridge, SNS |
| Dashboard | React (planned) |
| Storage | DynamoDB, S3 |
| Auth | Amazon Cognito |

## Contributing

1. Read the constitution (`.specify/memory/constitution.md`)
2. Create a feature spec following the template
3. Get spec approved before implementation
4. Follow conventional commits with logical chunks
5. Ensure all verification gates pass

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
