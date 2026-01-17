# Research: Agent Framework

**Feature**: 001-agent-framework
**Date**: 2026-01-16
**Status**: Complete

## Research Areas

### 1. AgentCore A2A Protocol and Agent Cards

**Decision**: Use native AgentCore A2A protocol with Agent Cards served at `/.well-known/agent-card.json`

**Rationale**:

- AgentCore provides built-in A2A support with standardized discovery mechanism
- Agent Cards support skills array with id, name, description, and tags
- JSON-RPC 2.0 over HTTP for agent-to-agent communication
- Supports both SigV4 and OAuth 2.0 authentication
- A2A servers run on port 9000, mounted at `/`

**Alternatives Considered**:

- Custom discovery mechanism: Rejected - would duplicate AgentCore functionality
- gRPC protocol: Rejected - A2A is the native protocol with better tooling support

**Key Implementation Details**:

```json
{
  "name": "Agent Name",
  "version": "1.0.0",
  "url": "https://bedrock-agentcore.region.amazonaws.com/runtimes/agent-arn/invocations/",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "capabilities": { "streaming": true },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    {
      "id": "skill-id",
      "name": "Skill Name",
      "description": "Skill capabilities",
      "tags": []
    }
  ]
}
```

---

### 2. Gateway Tool Discovery and Access

**Decision**: Use AgentCore Gateway with MCP protocol for tool discovery via `mcp_client.list_tools_sync()` and semantic search via `x_amz_bedrock_agentcore_search`

**Rationale**:

- Gateway provides unified tool interface across Lambda, APIs, and MCP servers
- Built-in semantic search for natural language tool discovery
- Pagination support for large tool catalogs
- Strands SDK provides synchronous wrappers (`list_tools_sync`, `call_tool_sync`)

**Alternatives Considered**:

- Direct Lambda invocation: Rejected - loses tool abstraction and discovery benefits
- Custom tool registry: Rejected - Gateway already provides this functionality

**Key Implementation Details**:

```python
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

def create_transport(url: str, token: str):
    return streamablehttp_client(url, headers={"Authorization": f"Bearer {token}"})

mcp_client = MCPClient(lambda: create_transport(url, token))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    result = mcp_client.call_tool_sync(
        tool_use_id="tool-123",
        name="tool_name",
        arguments={"arg": "value"}
    )
```

---

### 3. Custom Metadata Storage

**Decision**: Use DynamoDB for custom agent metadata (enhanced input/output schemas, consultation requirements) with agent name as partition key

**Rationale**:

- Agent Cards have fixed schema - custom fields require separate storage
- DynamoDB provides fast key-value lookup (< 10ms) meeting 500ms discovery SLA
- Single-table design keeps metadata co-located and queryable
- GSI on skill IDs enables skill-based agent lookup

**Alternatives Considered**:

- Extend Agent Card JSON: Rejected - non-standard, may break A2A compatibility
- AgentCore Memory: Better suited for session/conversation data, not static metadata
- S3 JSON files: Rejected - slower for frequent lookups, no query capability

**Schema Design**:

```
Table: AgentMetadata
  PK: agent_name (String)

Attributes:
  - input_schemas: List<InputSchema>
  - output_schemas: List<OutputSchema>
  - consultation_requirements: List<ConsultationRule>
  - created_at: ISO8601 timestamp
  - updated_at: ISO8601 timestamp
  - version: String (matches Agent Card version)

GSI: SkillIndex
  PK: skill_id
  Projects: agent_name, skill_id
```

---

### 4. Memory Service Integration

**Decision**: Use AgentCore Memory for agent state and conversation history; separate from custom metadata

**Rationale**:

- Memory service supports short-term (session) and long-term (cross-session) persistence
- Built-in strategies: summary, user preference, semantic extraction
- Native Strands SDK integration via `AgentCoreMemorySessionManager`
- Supports shared memory across agents via namespaces

**Alternatives Considered**:

- Redis for session state: Rejected - AgentCore Memory is purpose-built for agents
- DynamoDB for all data: Rejected - Memory service provides richer conversation handling

**Key Implementation Details**:

```python
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

client = MemoryClient(region_name="us-east-1")
memory = client.create_memory(
    name="AgentMemory",
    description="Memory for agent state",
    strategies=[
        {"summaryMemoryStrategy": {"name": "SessionSummarizer", "namespaces": ["/summaries/{actorId}/{sessionId}"]}},
        {"semanticMemoryStrategy": {"name": "FactExtractor", "namespaces": ["/facts/{actorId}"]}}
    ]
)
```

---

### 5. Consultation Enforcement Mechanism

**Decision**: Build custom consultation rules engine that validates A2A message logs in AgentCore Observability before allowing task completion

**Rationale**:

- A2A enables agent-to-agent calls but doesn't enforce "who must call whom"
- Observability traces all A2A messages with timestamps and outcomes
- Rules engine queries Observability to verify required consultations occurred
- Integrates with workflow engine (Feature 005) for completion gates

**Alternatives Considered**:

- Cedar policies: Could work for access control but not "must consult" enforcement
- Workflow-only enforcement: Rejected - rules should be agent-level, not workflow-specific

**Architecture**:

```
Agent attempts task completion
  ↓
Consultation Rules Engine triggered
  ↓
Query agent's consultation requirements (DynamoDB)
  ↓
Query Observability for A2A traces matching task
  ↓
Verify all mandatory consultations have "approved" outcome
  ↓
Allow/Block completion based on verification
```

---

### 6. Agent Deployment Pattern

**Decision**: Use `@app.entrypoint` decorator with Agent Card JSON served by the runtime

**Rationale**:

- Native AgentCore deployment pattern for serverless agents
- Agent Card automatically served at `/.well-known/agent-card.json`
- Supports versioning via Agent Card `version` field
- Runtime handles scaling, security, and observability

**Key Implementation Details**:

```python
from bedrock_agentcore.runtime import Runtime, InvocationContext, InvocationResponse

app = Runtime()

@app.entrypoint
async def handle_request(context: InvocationContext) -> InvocationResponse:
    # Agent logic here
    return InvocationResponse(
        output={"message": {"content": [{"type": "text", "text": "Response"}]}}
    )

# Agent Card defined in separate JSON file, referenced at deployment
```

---

### 7. Testing Strategy

**Decision**: Use moto for AWS service mocking, pytest-asyncio for async tests, contract tests for schemas

**Rationale**:

- moto provides comprehensive AWS service mocks including DynamoDB
- pytest-asyncio supports AgentCore's async patterns
- Contract tests ensure Agent Card and metadata schemas remain valid
- Integration tests against LocalStack where possible, and actual AWS for E2E validation. AWS integration tests are required, following the following process:
  - CDK creates a stack and deploys all resources
  - Integration tests run against deployed resources
  - Stack is torn down after tests complete (even on test failure)

**AWS Integration Test Guardrails**:

- **When to run**: On pull requests to main, not on every commit
- **Stack naming**: `AgentFramework-Test-{branch}-{timestamp}` for isolation and easy cleanup
- **Automation**: Once working locally, automate via GitHub Actions as a required quality gate before merge
- **Cleanup**: Teardown runs unconditionally (finally block); nightly job cleans orphaned test stacks older than 24h

**CI/CD Pipeline** (target state):

```
PR opened/updated
  ↓
Unit tests + Contract tests (fast, no AWS)
  ↓
AWS Integration tests (GitHub Action)
  ├─ CDK deploy test stack
  ├─ Run integration tests
  └─ CDK destroy test stack (always)
  ↓
All pass → Ready for review/merge
```

**GitHub Actions Workflow Blueprint**:

```yaml
name: Agent Framework CI

on:
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'infrastructure/**'
  workflow_dispatch:

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run unit + contract tests with coverage
        run: |
          pytest tests/unit tests/contract \
            --cov=src --cov-report=xml --cov-report=html \
            --cov-fail-under=80 \
            --junitxml=test-results.xml

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: |
            htmlcov/
            coverage.xml
            test-results.xml
          retention-days: 7

  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    needs: unit-tests  # Only run if unit tests pass
    permissions:
      id-token: write  # For OIDC auth to AWS
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Setup Node.js (for CDK)
        uses: actions/setup-node@v4
        with:
          node-version: '24'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          npm install -g aws-cdk

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_TEST_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy test stack
        id: deploy
        run: |
          STACK_NAME="AgentFramework-Test-${{ github.head_ref }}-$(date +%s)"
          echo "stack_name=$STACK_NAME" >> $GITHUB_OUTPUT
          cd infrastructure/cdk
          cdk deploy $STACK_NAME --require-approval never

      - name: Run integration tests
        run: pytest tests/integration -v --tb=short

      - name: Destroy test stack
        if: always()
        run: |
          cd infrastructure/cdk
          cdk destroy ${{ steps.deploy.outputs.stack_name }} --force

  report:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    if: always() && github.event_name == 'pull_request'
    steps:
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const unitResult = '${{ needs.unit-tests.result }}';
            const integrationResult = '${{ needs.integration-tests.result }}';

            let body = '## 🧪 Test Results\n\n';
            body += `| Suite | Status |\n|-------|--------|\n`;
            body += `| Unit + Contract | ${unitResult === 'success' ? '✅' : '❌'} ${unitResult} |\n`;
            body += `| AWS Integration | ${integrationResult === 'success' ? '✅' : '❌'} ${integrationResult} |\n`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

      - name: Create summary
        run: |
          echo "## Agent Framework CI Summary" >> $GITHUB_STEP_SUMMARY
          echo "| Suite | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| Unit + Contract | ${{ needs.unit-tests.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| AWS Integration | ${{ needs.integration-tests.result }} |" >> $GITHUB_STEP_SUMMARY
```

**Alternatives Considered**:

- AWS SAM Local: Good for Lambda but doesn't cover AgentCore services
- Real AWS for all tests: Too slow and costly for unit tests
- Skip AWS tests in CI: Rejected - would miss real permission/integration issues

**Test Coverage**:

- **Tool**: pytest-cov (generates coverage reports)
- **Minimum threshold**: 80% line coverage for new code (enforced in CI)
- **Reports**:
  - HTML report for local development (`htmlcov/`)
  - XML report for CI integration (Codecov, GitHub Actions summary)
  - Coverage diff on PRs showing impact of changes
- **Exclusions**: Infrastructure code (CDK), test files themselves

**Test Structure**:

```
tests/
├── unit/           # Fast, mocked tests (run on every commit)
├── integration/    # LocalStack and AWS tests (run on PR)
└── contract/       # Schema validation tests (run on every commit)
```

---

## Open Questions Resolved

| Question                           | Resolution                                                   |
| ---------------------------------- | ------------------------------------------------------------ |
| Where to store custom metadata?    | DynamoDB with agent_name as PK                               |
| How to enforce consultations?      | Query Observability for A2A traces                           |
| Which MCP client to use?           | Strands SDK MCPClient with sync wrappers                     |
| How to handle tool unavailability? | Gateway returns error, agent handles gracefully              |
| Memory vs custom metadata storage? | Memory for state/conversations, DynamoDB for static metadata |

## Dependencies Identified

| Dependency                   | Version | Purpose                       |
| ---------------------------- | ------- | ----------------------------- |
| bedrock-agentcore-sdk-python | latest  | Core AgentCore functionality  |
| strands                      | latest  | MCP client with sync wrappers |
| boto3                        | 1.34+   | AWS service access            |
| pydantic                     | 2.0+    | Data validation and schemas   |
| moto                         | 5.0+    | AWS mocking for tests         |
| pytest-asyncio               | 0.23+   | Async test support            |
| pytest-cov                   | 4.0+    | Coverage reporting            |

## Next Steps

1. Create data-model.md with entity definitions
2. Generate API contracts (OpenAPI for registry API, JSON schemas for Agent Card extensions)
3. Create quickstart.md with setup instructions
