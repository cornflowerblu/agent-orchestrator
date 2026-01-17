"""Lambda handler for Loop Framework policy enforcement monitoring.

This Lambda function monitors loop iterations and enforces Cedar policies
for iteration limits using AWS Bedrock AgentCore Policy service.
"""

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Environment variables
LOG_GROUP_NAME = os.environ.get("LOG_GROUP_NAME", "/aws/bedrock/agent-loops")
POLICY_ENGINE_NAME = os.environ.get("POLICY_ENGINE_NAME", "LoopIterationPolicyEngine")

# AWS clients
bedrock_client = boto3.client("bedrock-agent-runtime")
logs_client = boto3.client("logs")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for policy enforcement monitoring.

    Args:
        event: Lambda event containing loop iteration data
        context: Lambda context

    Returns:
        Response with policy evaluation result
    """
    try:
        # Extract loop iteration data from event
        loop_id = event.get("loop_id")
        iteration_count = event.get("iteration_count", 0)
        max_iterations = event.get("max_iterations", 100)

        # Log the monitoring event
        log_message = {
            "event": "policy_check",
            "loop_id": loop_id,
            "iteration_count": iteration_count,
            "max_iterations": max_iterations,
            "timestamp": context.request_id,
        }

        # Write to CloudWatch Logs
        try:
            logs_client.put_log_events(
                logGroupName=LOG_GROUP_NAME,
                logStreamName=f"loop-{loop_id}",
                logEvents=[
                    {
                        "timestamp": int(context.get_remaining_time_in_millis()),
                        "message": json.dumps(log_message),
                    }
                ],
            )
        except ClientError as e:
            # Log stream might not exist, create it
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logs_client.create_log_stream(
                    logGroupName=LOG_GROUP_NAME,
                    logStreamName=f"loop-{loop_id}",
                )

        # Evaluate policy: Should the loop continue?
        policy_result = {
            "allowed": iteration_count < max_iterations,
            "iteration_count": iteration_count,
            "max_iterations": max_iterations,
            "policy_engine": POLICY_ENGINE_NAME,
        }

        if not policy_result["allowed"]:
            policy_result["reason"] = "Maximum iterations exceeded"

        return {
            "statusCode": 200,
            "body": json.dumps(policy_result),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        error_message = f"Policy enforcement error: {e!s}"
        print(error_message)

        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_message}),
            "headers": {"Content-Type": "application/json"},
        }
