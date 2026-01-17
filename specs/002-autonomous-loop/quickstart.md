# Quickstart: Agent Loop Framework

**Branch**: `002-autonomous-loop` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)

## Overview

This guide shows how to implement autonomous execution loops in your agents using the Agent Loop Framework. The framework integrates with AgentCore services:

- **Memory** - Checkpoint persistence for recovery
- **Observability** - Progress tracking via OTEL traces
- **Policy** - Iteration limit enforcement via Cedar rules
- **Gateway/Code Interpreter** - Verification tool execution

## Prerequisites

```bash
# Install dependencies
pip install bedrock-agentcore opentelemetry-api opentelemetry-sdk pydantic

# AWS credentials configured
aws configure

# AgentCore services available in your region
export AWS_REGION=us-east-1
```

---

## Quick Example

```python
"""Minimal agent implementing autonomous loop."""

from src.loop.framework import LoopFramework
from src.loop.models import (
    LoopConfig,
    ExitConditionConfig,
    ExitConditionType,
)


async def main():
    # 1. Configure the loop
    config = LoopConfig(
        agent_name="code-fixer-agent",
        max_iterations=50,
        checkpoint_interval=5,
        exit_conditions=[
            ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
            ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
        ],
    )

    # 2. Initialize the framework
    framework = await LoopFramework.initialize(config)

    # 3. Run the loop
    result = await framework.run(
        work_function=do_work,
        initial_state={"files_to_fix": ["src/main.py", "src/utils.py"]},
    )

    # 4. Check the result
    if result.is_success():
        print(f"Completed in {result.iterations_completed} iterations!")
    else:
        print(f"Stopped: {result.outcome} after {result.iterations_completed} iterations")


async def do_work(iteration: int, state: dict, framework: LoopFramework) -> dict:
    """Work to perform each iteration. Return updated state."""
    # Your agent logic here
    file = state["files_to_fix"][iteration % len(state["files_to_fix"])]
    print(f"Iteration {iteration}: Processing {file}")

    # Modify state as needed
    state["last_processed"] = file
    return state


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Step-by-Step Guide

### Step 1: Define Exit Conditions

Exit conditions determine when your loop completes successfully. The framework supports standard verification tools:

```python
from src.loop.models import ExitConditionConfig, ExitConditionType

# Run pytest - loop exits when all tests pass
tests_pass = ExitConditionConfig(
    type=ExitConditionType.ALL_TESTS_PASS,
    tool_arguments={"markers": "not integration", "verbose": True},
    description="All unit tests must pass",
)

# Run ruff - loop exits when linting is clean
lint_clean = ExitConditionConfig(
    type=ExitConditionType.LINTING_CLEAN,
    tool_arguments={"paths": ["src/"]},
    description="No linting errors",
)

# Run build command - loop exits when build succeeds
build_ok = ExitConditionConfig(
    type=ExitConditionType.BUILD_SUCCEEDS,
    tool_name="npm",
    tool_arguments={"command": "run build"},
    description="Project builds without errors",
)

# Run security scanner via MCP
security_ok = ExitConditionConfig(
    type=ExitConditionType.SECURITY_SCAN_CLEAN,
    tool_name="snyk",  # Discovered via Gateway
    description="No security vulnerabilities",
)

# Custom condition with your own evaluator
custom = ExitConditionConfig(
    type=ExitConditionType.CUSTOM,
    custom_evaluator="myagent.checks.verify_coverage",
    description="Code coverage above 80%",
)
```

### Step 2: Configure the Loop

```python
from src.loop.models import LoopConfig

config = LoopConfig(
    # Required
    agent_name="my-agent",

    # Iteration limits (enforced by Cedar Policy)
    max_iterations=100,  # Default: 100

    # Checkpoint settings (saved to AgentCore Memory)
    checkpoint_interval=5,  # Save every 5 iterations
    checkpoint_expiry_seconds=86400,  # Keep for 24 hours

    # Exit conditions
    exit_conditions=[tests_pass, lint_clean],

    # Timeouts
    iteration_timeout_seconds=300,  # 5 min per iteration
    verification_timeout_seconds=30,  # 30s per tool (SC-002)

    # AgentCore configuration
    region="us-east-1",
    policy_engine_arn="arn:aws:bedrock-agentcore:us-east-1:123456789:policy-engine/loop-limits",
    gateway_url="https://gateway.agentcore.us-east-1.amazonaws.com",

    # Custom metadata (included in checkpoints and traces)
    custom_metadata={
        "project": "my-project",
        "task_id": "TASK-123",
    },
)
```

### Step 3: Initialize the Framework

```python
from src.loop.framework import LoopFramework

# Async initialization (connects to AgentCore services)
framework = await LoopFramework.initialize(config)

# Or sync if you're in a sync context
framework = LoopFramework.initialize_sync(config)
```

The framework initialization:
1. Creates a Memory for checkpoints (or reuses existing)
2. Sets up OTEL tracer for Observability
3. Validates Policy engine connection (if configured)
4. Discovers verification tools via Gateway

### Step 4: Implement Your Work Function

```python
async def do_work(
    iteration: int,
    state: dict,
    framework: LoopFramework,
) -> dict:
    """
    Called each iteration. Return updated state.

    Args:
        iteration: Current iteration number (0-indexed)
        state: Agent state from previous iteration (or initial_state)
        framework: Access to checkpoint and logging helpers

    Returns:
        Updated state dict for next iteration

    Raises:
        Any exception will trigger error handling (checkpoint saved, loop stopped)
    """
    # Access current exit condition status
    conditions = framework.get_exit_condition_status()
    for cond in conditions:
        print(f"  {cond.type}: {cond.status}")

    # Do your work
    files_changed = await fix_code_issues(state)

    # Update state
    state["files_changed"] = state.get("files_changed", 0) + files_changed
    state["last_iteration"] = iteration

    # Optionally save checkpoint with custom data
    if iteration % 10 == 0:
        await framework.save_checkpoint(
            custom_data={"milestone": f"iteration-{iteration}"}
        )

    return state
```

### Step 5: Run the Loop

```python
from src.loop.models import LoopResult

result: LoopResult = await framework.run(
    work_function=do_work,
    initial_state={
        "target_files": ["src/main.py"],
        "files_changed": 0,
    },
)

# Check outcome
match result.outcome:
    case LoopOutcome.COMPLETED:
        print("All exit conditions met!")
    case LoopOutcome.ITERATION_LIMIT:
        print(f"Hit iteration limit at {result.iterations_completed}")
    case LoopOutcome.ERROR:
        print(f"Error: {result.error_message}")
    case LoopOutcome.CANCELLED:
        print("Loop was cancelled")
    case LoopOutcome.TIMEOUT:
        print("Overall timeout exceeded")

# Access final state
print(f"Files changed: {result.final_state.get('files_changed')}")

# View condition results
for cond in result.final_exit_conditions:
    print(f"  {cond.type}: {cond.status} (iteration {cond.iteration_evaluated})")
```

---

## Recovery from Checkpoints

If your agent is interrupted, you can resume from the last checkpoint:

```python
# Check for existing checkpoint
checkpoint = await framework.load_checkpoint(session_id="previous-session-id")

if checkpoint:
    print(f"Resuming from iteration {checkpoint.iteration}")
    result = await framework.run(
        work_function=do_work,
        resume_from=checkpoint,  # Resume from checkpoint
    )
else:
    # Start fresh
    result = await framework.run(
        work_function=do_work,
        initial_state={"start": "fresh"},
    )
```

The framework automatically:
- Saves checkpoints every `checkpoint_interval` iterations
- Stores checkpoints in AgentCore Memory (short-term)
- Includes all exit condition statuses in checkpoints
- Restores within one iteration of the checkpoint (SC-006)

---

## Monitoring Progress

### From Your Agent

```python
# Get current loop state
state = framework.get_state()
print(f"Iteration: {state.current_iteration}/{state.max_iterations}")
print(f"Phase: {state.phase}")
print(f"Active: {state.is_active}")

# Check warning threshold (80% of iterations used)
if state.at_warning_threshold():
    print("Warning: Approaching iteration limit!")

# Emit custom trace event
await framework.emit_event(
    event_type=IterationEventType.CHECKPOINT_SAVED,
    details={"reason": "manual save"},
)
```

### From Dashboard (Querying Observability)

```python
from src.dashboard.queries import ObservabilityQueries

queries = ObservabilityQueries(region="us-east-1")

# Get progress for a specific session
progress = await queries.get_loop_progress(session_id="loop-session-123")
print(f"Iteration: {progress.current_iteration}/{progress.max_iterations}")
print(f"Progress: {progress.progress_percentage}%")

# Get recent events
events = await queries.get_recent_events(
    session_id="loop-session-123",
    limit=10,
)
for event in events:
    print(f"  {event.timestamp}: {event.event_type}")

# Get checkpoint history
checkpoints = await queries.list_checkpoints(session_id="loop-session-123")
for cp in checkpoints:
    print(f"  Checkpoint at iteration {cp.iteration}: {cp.created_at}")
```

---

## Policy Enforcement

Iteration limits are enforced by AgentCore Policy using Cedar rules:

```python
from src.orchestrator.policy import PolicyEnforcer

# Setup policy for your agent
enforcer = PolicyEnforcer(
    policy_engine_arn="arn:aws:bedrock-agentcore:...",
    region="us-east-1",
)

# Create iteration limit policy
await enforcer.create_iteration_policy(
    agent_name="my-agent",
    max_iterations=100,
)

# The framework automatically checks policy each iteration
# If limit exceeded, agent receives PolicyViolation exception
```

### Handling Policy Violations

```python
from src.exceptions import PolicyViolationError

try:
    result = await framework.run(work_function=do_work, initial_state={})
except PolicyViolationError as e:
    print(f"Policy stopped execution: {e.details}")
    # Save final state, cleanup, etc.
```

---

## Verification Tools

### Using Code Interpreter (Sandboxed)

```python
from src.loop.conditions import ExitConditionEvaluator

evaluator = ExitConditionEvaluator(region="us-east-1")

# Run pytest in sandbox
result = await evaluator.evaluate_tests(
    test_path="tests/",
    markers="not integration",
)
print(f"Tests passed: {result.status == 'met'}")
print(f"Output: {result.tool_output}")

# Run ruff in sandbox
result = await evaluator.evaluate_linting(
    paths=["src/"],
)
print(f"Lint clean: {result.status == 'met'}")
```

### Using Gateway MCP Tools

```python
# Discover available tools
tools = await framework.discover_tools(
    query="security scanning vulnerability detection"
)
for tool in tools:
    print(f"Found: {tool.name} - {tool.description}")

# Invoke specific tool
result = await framework.invoke_tool(
    tool_name="snyk_scan",
    arguments={"path": "src/", "severity": "high"},
)
```

---

## Error Handling

```python
async def do_work(iteration: int, state: dict, framework: LoopFramework) -> dict:
    try:
        # Your work
        result = await process_file(state["current_file"])
        state["processed"].append(result)

    except RecoverableError as e:
        # Log and continue to next iteration
        await framework.log_warning(f"Recoverable error: {e}")
        state["errors"].append(str(e))

    except UnrecoverableError as e:
        # This will stop the loop with ERROR outcome
        raise

    return state
```

The framework handles errors by:
1. Saving a checkpoint (if possible)
2. Logging to Observability
3. Returning `LoopResult` with `outcome=ERROR`

---

## Best Practices

### 1. Keep State Serializable

```python
# Good - JSON serializable
state = {
    "files": ["a.py", "b.py"],
    "count": 5,
    "metadata": {"key": "value"},
}

# Bad - not serializable
state = {
    "connection": db_connection,  # Can't serialize
    "callback": my_function,      # Can't serialize
}
```

### 2. Idempotent Work Functions

```python
async def do_work(iteration: int, state: dict, framework: LoopFramework) -> dict:
    # Check if already processed (idempotent)
    if state.get("iteration_complete", -1) >= iteration:
        return state  # Already done, skip

    # Do work
    result = await process()

    # Mark complete
    state["iteration_complete"] = iteration
    return state
```

### 3. Progressive Exit Conditions

Order exit conditions from fastest to slowest:

```python
config = LoopConfig(
    exit_conditions=[
        # Fast checks first
        ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
        # Slower checks after
        ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
        # Slowest last
        ExitConditionConfig(type=ExitConditionType.SECURITY_SCAN_CLEAN),
    ],
)
```

### 4. Reasonable Iteration Limits

```python
# Task-appropriate limits
config = LoopConfig(
    # Quick fixes: 10-25 iterations
    # Code generation: 25-50 iterations
    # Complex refactoring: 50-100 iterations
    # Research tasks: 100+ iterations
    max_iterations=50,
)
```

---

## Complete Example: TDD Agent

```python
"""Agent that implements TDD workflow using Loop Framework."""

from src.loop.framework import LoopFramework
from src.loop.models import (
    LoopConfig,
    ExitConditionConfig,
    ExitConditionType,
    LoopOutcome,
)


async def tdd_agent():
    """Run TDD workflow: write test -> implement -> verify -> repeat."""

    config = LoopConfig(
        agent_name="tdd-agent",
        max_iterations=75,
        checkpoint_interval=5,
        exit_conditions=[
            ExitConditionConfig(
                type=ExitConditionType.ALL_TESTS_PASS,
                tool_arguments={"markers": "not integration"},
                description="All unit tests pass",
            ),
            ExitConditionConfig(
                type=ExitConditionType.LINTING_CLEAN,
                description="No linting errors",
            ),
        ],
        custom_metadata={"workflow": "tdd"},
    )

    framework = await LoopFramework.initialize(config)

    result = await framework.run(
        work_function=tdd_iteration,
        initial_state={
            "phase": "write_test",
            "test_file": "tests/test_feature.py",
            "impl_file": "src/feature.py",
            "tests_written": 0,
            "implementations": 0,
        },
    )

    print(result.summary())
    return result


async def tdd_iteration(
    iteration: int,
    state: dict,
    framework: LoopFramework,
) -> dict:
    """Single TDD iteration: cycle through write/implement/refactor."""

    phase = state["phase"]

    if phase == "write_test":
        # Write a failing test
        await write_next_test(state["test_file"])
        state["tests_written"] += 1
        state["phase"] = "implement"

    elif phase == "implement":
        # Implement code to pass the test
        await implement_feature(state["impl_file"])
        state["implementations"] += 1
        state["phase"] = "verify"

    elif phase == "verify":
        # Check if we can continue or need to fix
        conditions = framework.get_exit_condition_status()
        tests_pass = next(
            (c for c in conditions if c.type == ExitConditionType.ALL_TESTS_PASS),
            None,
        )

        if tests_pass and tests_pass.status == "not_met":
            # Tests still failing, keep implementing
            state["phase"] = "implement"
        else:
            # Tests pass, write next test
            state["phase"] = "write_test"

    return state


async def write_next_test(test_file: str):
    """Write the next failing test (your logic here)."""
    pass


async def implement_feature(impl_file: str):
    """Implement code to pass tests (your logic here)."""
    pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(tdd_agent())
```

---

## Troubleshooting

### Loop Not Starting

```python
# Check framework initialization
framework = await LoopFramework.initialize(config)
print(f"Session ID: {framework.session_id}")
print(f"Memory connected: {framework.memory_connected}")
print(f"Policy enforcer: {framework.policy_enabled}")
```

### Checkpoints Not Saving

```python
# Verify Memory service connection
from bedrock_agentcore.memory import MemoryClient
client = MemoryClient(region_name="us-east-1")
memories = client.list_memories()
print(f"Available memories: {len(memories)}")
```

### Exit Conditions Not Evaluating

```python
# Check tool availability
tools = await framework.list_available_tools()
for tool in tools:
    print(f"  {tool.name}: {tool.status}")

# Manual evaluation test
from src.loop.conditions import ExitConditionEvaluator
evaluator = ExitConditionEvaluator(region="us-east-1")
result = await evaluator.evaluate(ExitConditionType.ALL_TESTS_PASS)
print(f"Result: {result}")
```

### Policy Violations Unexpected

```python
# Check current policy
from src.orchestrator.policy import PolicyEnforcer
enforcer = PolicyEnforcer(policy_engine_arn="...", region="us-east-1")
policy = await enforcer.get_policy(agent_name="my-agent")
print(f"Max iterations: {policy.max_iterations}")
print(f"Mode: {'ENFORCE' if policy.enforce_mode else 'MONITOR'}")
```

---

## Next Steps

- See [data-model.md](./data-model.md) for detailed entity definitions
- See [research.md](./research.md) for AgentCore API patterns
- See [spec.md](./spec.md) for full requirements and acceptance criteria
