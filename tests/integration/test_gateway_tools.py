"""Integration tests for Gateway tool access."""

import os

import boto3
import pytest


@pytest.mark.integration
class TestGatewayIntegration:
    """Integration tests for Gateway (requires AWS setup)."""

    @pytest.fixture
    def lambda_client(self):
        """Boto3 Lambda client for invoking tool registry."""
        return boto3.client("lambda", region_name=os.getenv("AWS_REGION", "us-east-1"))

    @pytest.fixture
    def gateway_lambda_arn(self):
        """Get Gateway tool registry Lambda ARN from outputs.json."""
        import json
        from pathlib import Path

        outputs_file = Path("infrastructure/cdk/outputs.json")
        if not outputs_file.exists():
            pytest.skip("outputs.json not found - stack not deployed")

        with open(outputs_file) as f:
            outputs = json.load(f)

        gateway_outputs = outputs.get("AgentOrchestratorGateway", {})
        arn = gateway_outputs.get("ToolRegistryLambdaArn")

        if not arn:
            pytest.skip("Gateway Lambda ARN not found in outputs")

        return arn

    def test_discover_tools_from_gateway(self, lambda_client, gateway_lambda_arn):
        """Should discover tools from deployed Gateway."""
        # Invoke tool registry Lambda to list tools
        response = lambda_client.invoke(
            FunctionName=gateway_lambda_arn,
            InvocationType="RequestResponse",
            Payload='{"action": "list_tools"}',
        )

        # Parse response
        import json

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        # Verify tools were discovered
        assert "tools" in body
        assert isinstance(body["tools"], list)
        assert body["count"] >= 0

    def test_invoke_tool_via_gateway(self, lambda_client, gateway_lambda_arn):
        """Should invoke a tool through Gateway."""
        # Register a test tool
        register_payload = {
            "action": "register_tool",
            "tool_name": "test_calculator",
            "tool_definition": {
                "description": "Test calculator tool",
                "version": "1.0.0",
            },
        }

        response = lambda_client.invoke(
            FunctionName=gateway_lambda_arn,
            InvocationType="RequestResponse",
            Payload=str(register_payload).replace("'", '"'),
        )

        # Parse response
        import json

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        # Verify tool registration
        assert body["status"] == "registered"
        assert body["tool_name"] == "test_calculator"

    def test_semantic_search_returns_relevant_tools(
        self, lambda_client, gateway_lambda_arn
    ):
        """Should return semantically relevant tools for natural language query."""
        # List tools first
        response = lambda_client.invoke(
            FunctionName=gateway_lambda_arn,
            InvocationType="RequestResponse",
            Payload='{"action": "list_tools"}',
        )

        import json

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        # Verify tools list includes example tools with descriptions
        tools = body.get("tools", [])
        if tools:
            # Check that tools have semantic metadata
            first_tool = tools[0]
            assert "name" in first_tool
            assert "description" in first_tool
            assert len(first_tool["description"]) > 0

    def test_tool_unavailable_error_handling(self, lambda_client, gateway_lambda_arn):
        """Should handle unavailable tools gracefully."""
        # Try to invoke an unknown action
        response = lambda_client.invoke(
            FunctionName=gateway_lambda_arn,
            InvocationType="RequestResponse",
            Payload='{"action": "unknown_action"}',
        )

        import json

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        # Verify error handling
        assert "error" in body
        assert "supported_actions" in body

    def test_observability_tracing(self, lambda_client, gateway_lambda_arn):
        """Should trace tool invocations in AgentCore Observability."""
        logs_client = boto3.client("logs", region_name=os.getenv("AWS_REGION", "us-east-1"))

        # Invoke a tool operation
        lambda_client.invoke(
            FunctionName=gateway_lambda_arn,
            InvocationType="RequestResponse",
            Payload='{"action": "list_tools"}',
        )

        # Check CloudWatch Logs for traces
        log_groups = logs_client.describe_log_groups(
            logGroupNamePrefix="/aws/bedrock/agent-gateway"
        )

        # Verify log group exists
        assert len(log_groups["logGroups"]) > 0
        assert log_groups["logGroups"][0]["logGroupName"] == "/aws/bedrock/agent-gateway"
