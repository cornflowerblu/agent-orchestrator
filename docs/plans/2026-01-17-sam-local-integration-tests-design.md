# SAM Local Integration Tests Design

**Date:** 2026-01-17
**Status:** Draft
**Purpose:** Pre-deploy gate to catch packaging/config/integration issues before expensive CDK deploy

## Context

We have three testing layers:

```
Unit tests (fast, mocked, feedback loop)
    ↓ pass
SAM local invoke + LocalStack (pre-deploy gate, ~60s)  ← THIS DESIGN
    ↓ pass
CDK deploy + real AWS tests (expensive, real)
```

The current "local integration" tests mock everything and don't catch real issues. We want tests that:

- Run in ~60 seconds (acceptable for a gate)
- Catch packaging, handler entry point, and config issues
- Hit real DynamoDB API (via LocalStack)
- Run before committing to the CDK deploy cycle

## Architecture

```
pytest
    → SAMLocalInvoker.invoke()
        → subprocess: sam local invoke FunctionName
            → Docker container (Lambda runtime)
                → Your handler code
                    → LocalStack DynamoDB (localhost:4566)
```

## File Structure

```
tests/integration/sam_local/
├── __init__.py
├── conftest.py              # Fixtures: LocalStack, SAM invoker
├── test_registry_handlers.py # Handler integration tests
└── ...

infrastructure/sam-local/
├── template.yaml            # (existing)
├── samconfig.toml           # (existing)
└── docker-compose.yml       # LocalStack service
```

## Implementation

### conftest.py - Test Fixtures

```python
"""
SAM Local + LocalStack integration test fixtures.

Pre-deploy gate: catches packaging, config, and integration issues
before committing to full CDK deploy.
"""

import json
import subprocess
import time
from pathlib import Path

import boto3
import pytest

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SAM_LOCAL_DIR = PROJECT_ROOT / "infrastructure" / "sam-local"

LOCALSTACK_ENDPOINT = "http://localhost:4566"


# ============================================================
# LocalStack Management
# ============================================================

@pytest.fixture(scope="session")
def localstack():
    """Ensure LocalStack is running and healthy."""
    client = boto3.client(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    max_retries = 30
    for i in range(max_retries):
        try:
            client.list_tables()
            break
        except Exception:
            if i == max_retries - 1:
                pytest.fail(
                    "LocalStack not running. Start it with:\n"
                    "  docker compose -f infrastructure/sam-local/docker-compose.yml up -d"
                )
            time.sleep(1)

    return client


@pytest.fixture(scope="session")
def dynamodb_tables(localstack):
    """Create DynamoDB tables in LocalStack."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    tables_to_create = [
        {
            "TableName": "AgentMetadata",
            "KeySchema": [{"AttributeName": "agent_name", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "agent_name", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "AgentStatus",
            "KeySchema": [{"AttributeName": "agent_name", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "agent_name", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    ]

    for table_def in tables_to_create:
        try:
            dynamodb.create_table(**table_def)
        except localstack.exceptions.ResourceInUseException:
            pass  # Table already exists

    return dynamodb


# ============================================================
# SAM Local Invoker
# ============================================================

class SAMLocalInvoker:
    """Wrapper for sam local invoke commands."""

    def __init__(self, sam_dir: Path):
        self.sam_dir = sam_dir
        self._built = False

    def build(self, force: bool = False):
        """Run sam build if needed."""
        if self._built and not force:
            return

        result = subprocess.run(
            ["sam", "build"],
            cwd=self.sam_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"sam build failed:\n{result.stderr}")

        self._built = True

    def invoke(
        self,
        function_name: str,
        event: dict,
        timeout: int = 30,
    ) -> dict:
        """
        Invoke a Lambda function via sam local invoke.

        Returns parsed response dict with 'statusCode', 'body', etc.
        """
        self.build()

        event_json = json.dumps(event)

        result = subprocess.run(
            [
                "sam", "local", "invoke",
                function_name,
                "--event", "-",  # Read event from stdin
                "--docker-network", "host",
            ],
            cwd=self.sam_dir,
            input=event_json,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            # Check if it's a Lambda error vs invocation error
            if "FunctionError" in result.stdout:
                return self._parse_response(result.stdout)
            pytest.fail(
                f"sam local invoke failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        return self._parse_response(result.stdout)

    def _parse_response(self, output: str) -> dict:
        """Parse the Lambda response from sam local invoke output."""
        # sam local invoke outputs logs to stderr, response to stdout
        # The response is the last JSON object in stdout
        lines = output.strip().split("\n")

        # Find the JSON response (skip log lines)
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        pytest.fail(f"Could not parse Lambda response from:\n{output}")


@pytest.fixture(scope="session")
def sam_invoker():
    """SAM Local invoker instance."""
    return SAMLocalInvoker(SAM_LOCAL_DIR)


@pytest.fixture(scope="session")
def sam_ready(localstack, dynamodb_tables, sam_invoker):
    """
    Ensure everything is ready for SAM local tests.

    Use this as a dependency for all SAM local tests.
    """
    sam_invoker.build()
    return sam_invoker
```

### test_registry_handlers.py - Example Tests

```python
"""
SAM Local integration tests for registry API handlers.

These tests invoke actual Lambda functions via sam local invoke,
hitting LocalStack DynamoDB.
"""

import json

import pytest

pytestmark = [
    pytest.mark.integration_sam,
    pytest.mark.slow,
]


class TestListAgentsHandler:
    """Integration tests for ListAgentsFunction."""

    def test_list_agents_empty(self, sam_ready):
        """List agents returns empty list when no agents registered."""
        event = {
            "httpMethod": "GET",
            "path": "/agents",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_ready.invoke("ListAgentsFunction", event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["agents"] == []

    def test_list_agents_after_registration(self, sam_ready):
        """List agents returns registered agents."""
        # First, register an agent
        register_event = {
            "httpMethod": "PUT",
            "path": "/agents/test-agent/metadata",
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({
                "version": "1.0.0",
                "input_schemas": [],
                "output_schemas": [],
            }),
        }
        sam_ready.invoke("UpdateMetadataFunction", register_event)

        # Now list
        list_event = {
            "httpMethod": "GET",
            "path": "/agents",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_ready.invoke("ListAgentsFunction", list_event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["agents"]) >= 1
        agent_names = [a["agent_name"] for a in body["agents"]]
        assert "test-agent" in agent_names


class TestGetAgentHandler:
    """Integration tests for GetAgentFunction."""

    def test_get_agent_not_found(self, sam_ready):
        """Get non-existent agent returns 404."""
        event = {
            "httpMethod": "GET",
            "path": "/agents/nonexistent-agent",
            "pathParameters": {"agent_name": "nonexistent-agent"},
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_ready.invoke("GetAgentFunction", event)

        assert response["statusCode"] == 404

    def test_get_agent_success(self, sam_ready):
        """Get existing agent returns agent data."""
        # Register first
        register_event = {
            "httpMethod": "PUT",
            "path": "/agents/get-test-agent/metadata",
            "pathParameters": {"agent_name": "get-test-agent"},
            "body": json.dumps({
                "version": "2.0.0",
                "input_schemas": [],
                "output_schemas": [],
            }),
        }
        sam_ready.invoke("UpdateMetadataFunction", register_event)

        # Now get
        get_event = {
            "httpMethod": "GET",
            "path": "/agents/get-test-agent",
            "pathParameters": {"agent_name": "get-test-agent"},
            "queryStringParameters": None,
            "body": None,
        }

        response = sam_ready.invoke("GetAgentFunction", get_event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["agent_name"] == "get-test-agent"
        assert body["version"] == "2.0.0"


class TestUpdateMetadataHandler:
    """Integration tests for UpdateMetadataFunction."""

    def test_update_metadata_creates_new(self, sam_ready):
        """Update metadata creates new agent if not exists."""
        event = {
            "httpMethod": "PUT",
            "path": "/agents/new-agent/metadata",
            "pathParameters": {"agent_name": "new-agent"},
            "body": json.dumps({
                "version": "1.0.0",
                "input_schemas": [],
                "output_schemas": [],
            }),
        }

        response = sam_ready.invoke("UpdateMetadataFunction", event)

        assert response["statusCode"] in [200, 201]

    def test_update_metadata_invalid_body(self, sam_ready):
        """Update metadata with invalid JSON returns 400."""
        event = {
            "httpMethod": "PUT",
            "path": "/agents/bad-agent/metadata",
            "pathParameters": {"agent_name": "bad-agent"},
            "body": "not valid json",
        }

        response = sam_ready.invoke("UpdateMetadataFunction", event)

        assert response["statusCode"] == 400
```

### docker-compose.yml - LocalStack Service

```yaml
# infrastructure/sam-local/docker-compose.yml
services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    environment:
      - SERVICES=dynamodb
      - DEBUG=1
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
```

### pytest.ini - Markers

```ini
[pytest]
markers =
    integration_sam: SAM local invoke integration tests (require LocalStack)
    slow: marks tests as slow
```

## Usage

```bash
# One-time: start LocalStack
docker compose -f infrastructure/sam-local/docker-compose.yml up -d

# Run the SAM local integration tests
pytest tests/integration/sam_local -m integration_sam -v

# Or as part of your pre-deploy gate
pytest tests/unit && pytest tests/integration/sam_local -m integration_sam && cdk deploy
```

## What This Catches

Issues that mocked tests miss:

| Issue | Mocked Tests | SAM Local Tests |
|-------|--------------|-----------------|
| Handler entry point typo in template.yaml | ❌ | ✅ |
| Missing import in packaged Lambda | ❌ | ✅ |
| Environment variable misconfiguration | ❌ | ✅ |
| DynamoDB API quirks (moto vs real) | ❌ | ✅ |
| JSON serialization edge cases | ❌ | ✅ |
| Cold start issues | ❌ | ✅ |

## Future Considerations

- **CI Integration:** Add a CI job that runs these tests before deploy jobs
- **Table Cleanup:** Add fixture to clean tables between test classes for isolation
- **Parallel Execution:** SAM local invoke is slow; consider `pytest-xdist` with caution
- **Testcontainers:** Could replace docker-compose with testcontainers-python for self-contained tests
