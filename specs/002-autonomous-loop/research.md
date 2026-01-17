# Research: Autonomous Loop Execution

**Feature Branch**: `002-autonomous-loop`
**Research Date**: 2026-01-17
**Sources**: AWS Bedrock AgentCore Developer Guide, AgentCore SDK Documentation

## Research Summary

This document consolidates research findings for implementing the Autonomous Loop Framework using AgentCore services.

---

## 1. AgentCore Memory API - Checkpoint Storage

### Decision
Use AgentCore Memory service (short-term) for checkpoint persistence. The SDK provides `MemoryClient` for creating memories and `create_event` for storing checkpoint data.

### Rationale
- Native AgentCore service with built-in session management
- Event-based storage model fits checkpoint semantics (iteration snapshots)
- `eventExpiryDuration` allows automatic cleanup of old checkpoints
- Supports custom payload data for storing agent state

### API Patterns

```python
from bedrock_agentcore.memory import MemoryClient

# Initialize client
client = MemoryClient(region_name="us-east-1")

# Create memory for agent checkpoints
memory = client.create_memory(
    name="AgentLoopCheckpoints",
    description="Checkpoint storage for autonomous loop execution",
    eventExpiryDuration=86400  # 24 hours
)

# Save checkpoint as event
client.create_event(
    memory_id=memory.get("id"),
    actor_id="agent-123",
    session_id="loop-session-456",
    messages=[
        (json.dumps({
            "iteration": 15,
            "state": {"progress": "50%", "files_modified": 3},
            "exit_conditions": {"all_tests_pass": False, "build_succeeds": True},
            "timestamp": "2026-01-17T10:30:00Z"
        }), "TOOL")
    ]
)
```

### Recovery Pattern

```python
# List events to find latest checkpoint
response = data_client.list_events(
    memoryId=memory_id,
    actorId=actor_id,
    sessionId=session_id,
    maxResults=1  # Get most recent
)
checkpoint = json.loads(response['events'][0]['payload'][0]['text'])
```

### Alternatives Considered
- **DynamoDB direct**: Rejected - would bypass AgentCore native capabilities
- **S3 for large state**: Consider for checkpoints > 400KB (DynamoDB item limit)

---

## 2. AgentCore Observability API - Progress Tracking

### Decision
Use OpenTelemetry instrumentation with AgentCore's native observability. Emit custom spans for iteration events, exit condition evaluations, and checkpoint saves.

### Rationale
- AgentCore auto-instruments common frameworks (Strands, LangChain)
- Custom spans can be added with standard OTEL API
- Session correlation via `session.id` baggage
- Dashboard can query traces via CloudWatch X-Ray integration

### OTEL Span Patterns

```python
from opentelemetry import trace, baggage, context

tracer = trace.get_tracer("agent-loop-framework")

# Set session ID for correlation
ctx = baggage.set_baggage("session.id", loop_session_id)

# Emit iteration event
with tracer.start_as_current_span("loop.iteration", context=ctx) as span:
    span.set_attribute("iteration.number", current_iteration)
    span.set_attribute("iteration.max", max_iterations)
    span.set_attribute("loop.agent_name", agent_name)
    # ... do iteration work ...
    span.set_status(trace.StatusCode.OK)

# Emit exit condition evaluation
with tracer.start_as_current_span("loop.exit_condition.evaluate") as span:
    span.set_attribute("condition.name", "all_tests_pass")
    span.set_attribute("condition.result", test_passed)
    span.set_attribute("condition.tool_used", "pytest")
```

### Key Trace Attributes
- `traceloop.span.kind`: "workflow" for loop, "tool" for verifications
- `gen_ai.operation.name`: "autonomous_loop"
- `session.id`: Loop session ID for correlation
- `PlatformType`: "AWS::BedrockAgentCore"

### Querying Traces (Dashboard)
Dashboard queries CloudWatch Logs Insights / X-Ray for traces with matching session ID.

---

## 3. AgentCore Policy (Cedar) - Iteration Limits

### Decision
Use Cedar policies attached to Gateway to enforce iteration limits. Policy checks context parameters on each tool invocation.

### Rationale
- Cedar provides fine-grained, deterministic access control
- Integrates with Gateway - intercepts every tool call
- Supports dynamic conditions (`when` clauses)
- Can be updated at runtime without agent redeployment

### Cedar Policy Pattern for Iteration Limit

```cedar
// Allow agent loop iterations up to configured maximum
permit(
  principal is AgentCore::Agent,
  action == AgentCore::Action::"loop_iteration",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:123456789:gateway/loop-gateway"
)
when {
  context.input.current_iteration < context.input.max_iterations
};

// Deny when iteration limit exceeded
forbid(
  principal is AgentCore::Agent,
  action == AgentCore::Action::"loop_iteration",
  resource
)
when {
  context.input.current_iteration >= context.input.max_iterations
};
```

### Policy Management

```python
from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient

policy_client = PolicyClient(region_name="us-east-1")

# Create policy engine
engine = policy_client.create_or_get_policy_engine(
    name="LoopIterationPolicyEngine",
    description="Enforces iteration limits for autonomous agent loops"
)

# Create Cedar policy
policy = policy_client.create_or_get_policy(
    policy_engine_id=engine["policyEngineId"],
    name="iteration_limit_policy",
    description="Limit agent to configured max iterations",
    definition={"cedar": {"statement": cedar_statement}}
)

# Attach to gateway in ENFORCE mode
gateway_client.update_gateway_policy_engine(
    gateway_identifier=gateway_id,
    policy_engine_arn=engine["policyEngineArn"]
)
```

### RuntimePolicyViolation Handling
When policy blocks iteration, agent receives error response with policy violation details. Agent should log to Observability and gracefully terminate.

---

## 4. AgentCore Code Interpreter - Verification Tools

### Decision
Use Code Interpreter for sandboxed execution of verification tools (pytest, ruff, build commands). The `code_session` context manager provides isolated execution environment.

### Rationale
- Sandboxed execution prevents untrusted code from affecting host
- Supports Python execution with pip packages
- Returns structured output (stdout, stderr, exitCode)
- State maintained between calls within session

### Verification Tool Pattern

```python
from bedrock_agentcore.tools.code_interpreter_client import code_session
import json

def verify_tests_pass(region: str = "us-east-1") -> bool:
    """Run pytest and return True if all tests pass."""
    with code_session(region) as code_client:
        response = code_client.invoke("executeCode", {
            "code": """
import subprocess
result = subprocess.run(
    ["pytest", "-v", "--tb=short", "-m", "not integration"],
    capture_output=True,
    text=True
)
print(f"EXIT_CODE:{result.returncode}")
print(f"STDOUT:{result.stdout}")
print(f"STDERR:{result.stderr}")
""",
            "language": "python",
            "clearContext": False
        })

    for event in response["stream"]:
        result = event["result"]
        if result.get("isError"):
            return False
        exit_code = parse_exit_code(result["structuredContent"]["stdout"])
        return exit_code == 0

def verify_linting_clean(region: str = "us-east-1") -> bool:
    """Run ruff linter and return True if no errors."""
    with code_session(region) as code_client:
        response = code_client.invoke("executeCode", {
            "code": """
import subprocess
result = subprocess.run(["ruff", "check", "src/"], capture_output=True, text=True)
print(f"EXIT_CODE:{result.returncode}")
""",
            "language": "python",
            "clearContext": False
        })
    # ... parse response ...
```

### Supported Verification Tools
- `pytest` - Unit and integration tests
- `ruff` - Linting and formatting
- `mypy` - Type checking
- Build commands (via subprocess)
- Custom scripts

### Timeouts
Default Code Interpreter timeout is 60 seconds. For long-running tests, consider chunking or parallel execution.

---

## 5. AgentCore Gateway - MCP Tool Discovery & Invocation

### Decision
Use Gateway with semantic search enabled for discovering and invoking external verification tools. MCP protocol provides standardized tool interface.

### Rationale
- Semantic search finds relevant tools by natural language query
- MCP standard allows third-party tool integration
- Gateway handles authentication and policy enforcement
- Tools can be Lambda functions, external APIs, or MCP servers

### Tool Discovery Pattern

```python
import requests

def discover_verification_tools(gateway_url: str, access_token: str) -> list:
    """Find available verification tools via semantic search."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": "discover-verification-tools",
        "method": "tools/call",
        "params": {
            "name": "x_amz_bedrock_agentcore_search",
            "arguments": {
                "query": "code verification testing linting security scan"
            }
        }
    }

    response = requests.post(gateway_url, headers=headers, json=payload)
    return response.json()["result"]
```

### Tool Invocation Pattern

```python
def invoke_tool(gateway_url: str, access_token: str, tool_name: str, args: dict) -> dict:
    """Invoke a specific tool via Gateway."""
    payload = {
        "jsonrpc": "2.0",
        "id": f"invoke-{tool_name}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }

    response = requests.post(
        gateway_url,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
        json=payload
    )
    return response.json()
```

### Using Strands MCP Client

```python
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url, headers={"Authorization": f"Bearer {token}"}))

with mcp_client:
    # List all available tools
    tools = mcp_client.list_tools_sync()

    # Call specific tool
    result = mcp_client.call_tool_sync(
        tool_use_id="verify-tests-001",
        name="pytest_runner",
        arguments={"test_path": "tests/", "markers": "not integration"}
    )
```

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Loop Framework                         │
├─────────────────────────────────────────────────────────────────┤
│  LoopFramework                                                   │
│  ├── initialize(config) ──────────────────┐                      │
│  ├── run_iteration() ─────────────────────┼──► Policy Check      │
│  ├── save_checkpoint(state) ──────────────┼──► Memory Service    │
│  ├── evaluate_exit_conditions() ──────────┼──► Code Interpreter  │
│  │                                        │    + Gateway Tools    │
│  └── emit_progress_event() ───────────────┼──► Observability     │
└───────────────────────────────────────────┼─────────────────────┘
                                            │
           AgentCore Services               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Memory      │  Observability  │  Policy   │  Code Int. │ Gateway│
│  (short-term)│  (OTEL traces)  │  (Cedar)  │  (sandbox) │ (MCP)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| How to store checkpoint state? | AgentCore Memory short-term events with JSON payload |
| How to emit custom traces? | Standard OTEL API with AgentCore auto-instrumentation |
| How to enforce iteration limits? | Cedar policy attached to Gateway in ENFORCE mode |
| How to run verification tools? | Code Interpreter for sandboxed execution |
| How to discover/invoke MCP tools? | Gateway semantic search + MCP protocol |

---

## Dependencies Identified

```toml
# pyproject.toml additions
[project.dependencies]
bedrock-agentcore = ">=1.2.0"
opentelemetry-api = ">=1.30.0"
opentelemetry-sdk = ">=1.30.0"
bedrock-agentcore-starter-toolkit = ">=0.1.0"  # For Policy client
```

---

## Next Steps

1. **Phase 1: data-model.md** - Define LoopConfig, Checkpoint, ExitCondition entities
2. **Phase 1: contracts/** - JSON schema for checkpoint format
3. **Phase 1: quickstart.md** - Developer guide for using Loop Framework
