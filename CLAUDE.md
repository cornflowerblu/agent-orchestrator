# agent-orchestrator Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-16

## Active Technologies
- Python 3.11+ (AgentCore SDK requirement) + bedrock-agentcore SDK (Memory, Observability, Policy, Gateway, Code Interpreter), boto3, pydantic (002-autonomous-loop)
- AgentCore Memory (short-term for checkpoints), DynamoDB (existing from 001 for agent metadata/status) (002-autonomous-loop)

- Python 3.11+ (AgentCore SDK requirement) + AWS Bedrock AgentCore SDK, boto3, pydantic (validation) (001-agent-framework)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (AgentCore SDK requirement): Follow standard conventions

## Recent Changes
- 002-autonomous-loop: Added Python 3.11+ (AgentCore SDK requirement) + bedrock-agentcore SDK (Memory, Observability, Policy, Gateway, Code Interpreter), boto3, pydantic

- 001-agent-framework: Added Python 3.11+ (AgentCore SDK requirement) + AWS Bedrock AgentCore SDK, boto3, pydantic (validation)

<!-- MANUAL ADDITIONS START -->

## Constitution

Before any implementation work, read `.specify/memory/constitution.md` for non-negotiable project principles including:
- **Gherkin syntax** for all user stories and acceptance criteria
- **Verification-first** - no claiming "done" without tests/linting passing
- **Conventional commits** with logical chunks (not monolithic commits)
- **Spec-driven flow** - spec → plan → tasks → implement

<!-- MANUAL ADDITIONS END -->
