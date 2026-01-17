"""SAM Local + LocalStack integration test fixtures.

Pre-deploy gate: catches packaging, config, and integration issues
before committing to full CDK deploy.

Prerequisites:
    1. Docker running
    2. LocalStack started: docker-compose -f infrastructure/sam-local/docker-compose.yml up -d
    3. Lambda packages built: cd infrastructure/sam-local && ./build.sh
"""

import json
import subprocess
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SAM_LOCAL_DIR = PROJECT_ROOT / "infrastructure" / "sam-local"
EVENTS_DIR = SAM_LOCAL_DIR / "events"

LOCALSTACK_ENDPOINT = "http://localhost:4566"


# ============================================================
# LocalStack Management
# ============================================================


def _localstack_healthy() -> bool:
    """Check if LocalStack is running and healthy."""
    try:
        client = boto3.client(
            "dynamodb",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.list_tables()
        return True
    except Exception:
        return False


def _sam_build_exists() -> bool:
    """Check if SAM build directory exists with built functions."""
    build_dir = SAM_LOCAL_DIR / ".aws-sam" / "build"
    return build_dir.exists() and (build_dir / "ListAgentsFunction").exists()


@pytest.fixture(scope="session")
def localstack():
    """Ensure LocalStack is running and healthy."""
    if not _localstack_healthy():
        pytest.skip(
            "LocalStack not running. Start it with:\n"
            "  docker-compose -f infrastructure/sam-local/docker-compose.yml up -d"
        )

    return boto3.client(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture(scope="session")
def sam_build():
    """Ensure SAM build exists."""
    if not _sam_build_exists():
        pytest.skip(
            "SAM build not found. Build it with:\n  cd infrastructure/sam-local && ./build.sh"
        )
    return True


# ============================================================
# SAM Local Invoker
# ============================================================


class SAMLocalInvoker:
    """Wrapper for sam local invoke commands."""

    def __init__(self, sam_dir: Path):
        self.sam_dir = sam_dir

    def invoke(
        self,
        function_name: str,
        event: dict,
        timeout: int = 60,
    ) -> dict:
        """
        Invoke a Lambda function via sam local invoke.

        Returns parsed response dict with 'statusCode', 'body', etc.
        """
        event_json = json.dumps(event)

        result = subprocess.run(
            [
                "sam",
                "local",
                "invoke",
                function_name,
                "--event",
                "-",  # Read event from stdin
                "--docker-network",
                "host",
            ],
            cwd=self.sam_dir,
            input=event_json,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # We handle return code manually
        )

        if result.returncode != 0:
            # Check if it's a Lambda error vs invocation error
            if "FunctionError" in result.stdout:
                return self._parse_response(result.stdout)
            pytest.fail(
                f"sam local invoke {function_name} failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        return self._parse_response(result.stdout)

    def invoke_with_event_file(
        self,
        function_name: str,
        event_file: str,
        timeout: int = 60,
    ) -> dict:
        """Invoke a Lambda function using an existing event file."""
        event_path = EVENTS_DIR / event_file

        result = subprocess.run(
            [
                "sam",
                "local",
                "invoke",
                function_name,
                "--event",
                str(event_path),
                "--docker-network",
                "host",
            ],
            cwd=self.sam_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # We handle return code manually
        )

        if result.returncode != 0:
            if "FunctionError" in result.stdout:
                return self._parse_response(result.stdout)
            pytest.fail(
                f"sam local invoke {function_name} failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        return self._parse_response(result.stdout)

    def _parse_response(self, output: str) -> dict:  # type: ignore[type-arg]
        """Parse the Lambda response from sam local invoke output."""
        # sam local invoke outputs logs to stderr, response to stdout
        # The response is the last JSON object in stdout
        lines = output.strip().split("\n")

        # Find the JSON response (skip log lines)
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("{"):
                try:
                    result: dict = json.loads(stripped)  # type: ignore[type-arg]
                    return result
                except json.JSONDecodeError:
                    continue

        pytest.fail(f"Could not parse Lambda response from:\n{output}")


@pytest.fixture(scope="session")
def sam_invoker(localstack, sam_build):
    """SAM Local invoker instance - requires LocalStack and build."""
    return SAMLocalInvoker(SAM_LOCAL_DIR)


# ============================================================
# Test Data Helpers
# ============================================================


@pytest.fixture
def clean_test_data(localstack):
    """Clean up test data before and after test."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    def cleanup():
        for table_name in ["AgentMetadata", "AgentStatus"]:
            try:
                table = dynamodb.Table(table_name)
                scan = table.scan()
                with table.batch_writer() as batch:
                    for item in scan.get("Items", []):
                        if "test" in item.get("agent_name", "").lower():
                            batch.delete_item(Key={"agent_name": item["agent_name"]})
            except ClientError:
                pass  # Table might not exist

    cleanup()
    yield
    cleanup()
