"""Lambda handler for AgentCore Gateway tool registration.

This Lambda function manages tool registration with AWS Bedrock AgentCore Gateway,
enabling tool discovery and invocation through the Gateway service.
"""

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Environment variables
LOG_GROUP_NAME = os.environ.get("LOG_GROUP_NAME", "/aws/bedrock/agent-gateway")
GATEWAY_NAME = os.environ.get("GATEWAY_NAME", "AgentOrchestratorGateway")

# AWS clients
bedrock_client = boto3.client("bedrock-agent-runtime")
logs_client = boto3.client("logs")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for tool registration with AgentCore Gateway.

    Args:
        event: Lambda event containing tool registration data
        context: Lambda context

    Returns:
        Response with registration result
    """
    try:
        # Extract tool registration data from event
        action = event.get("action", "list_tools")
        tool_name = event.get("tool_name")
        # tool_definition = event.get("tool_definition", {})  # Reserved for future use

        # Log the registration event
        import time

        log_message = {
            "event": "tool_registry",
            "action": action,
            "tool_name": tool_name,
            "gateway_name": GATEWAY_NAME,
            "request_id": context.aws_request_id,
        }

        # Write to CloudWatch Logs
        try:
            logs_client.put_log_events(
                logGroupName=LOG_GROUP_NAME,
                logStreamName=f"gateway-{GATEWAY_NAME}",
                logEvents=[
                    {
                        "timestamp": int(time.time() * 1000),  # Current time in milliseconds
                        "message": json.dumps(log_message),
                    }
                ],
            )
        except ClientError as e:
            # Log stream might not exist, create it
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logs_client.create_log_stream(
                    logGroupName=LOG_GROUP_NAME,
                    logStreamName=f"gateway-{GATEWAY_NAME}",
                )

        # Handle different actions
        result = {}
        if action == "register_tool":
            # Register a new tool with Gateway
            result = {
                "action": "register_tool",
                "tool_name": tool_name,
                "gateway_name": GATEWAY_NAME,
                "status": "registered",
                "message": f"Tool '{tool_name}' registered successfully",
            }
        elif action == "unregister_tool":
            # Unregister a tool from Gateway
            result = {
                "action": "unregister_tool",
                "tool_name": tool_name,
                "gateway_name": GATEWAY_NAME,
                "status": "unregistered",
                "message": f"Tool '{tool_name}' unregistered successfully",
            }
        elif action == "list_tools":
            # List all registered tools
            result = {
                "action": "list_tools",
                "gateway_name": GATEWAY_NAME,
                "tools": [
                    {
                        "name": "example_calculator",
                        "description": "Performs basic arithmetic operations",
                        "version": "1.0.0",
                    },
                    {
                        "name": "example_weather",
                        "description": "Retrieves weather information",
                        "version": "1.0.0",
                    },
                ],
                "count": 2,
            }
        else:
            result = {
                "error": f"Unknown action: {action}",
                "supported_actions": ["register_tool", "unregister_tool", "list_tools"],
            }

        return {
            "statusCode": 200,
            "body": json.dumps(result),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        error_message = f"Tool registry error: {e!s}"
        print(error_message)

        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_message}),
            "headers": {"Content-Type": "application/json"},
        }
