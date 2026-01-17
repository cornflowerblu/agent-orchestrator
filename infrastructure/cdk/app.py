#!/usr/bin/env python3
"""AWS CDK app entry point for Agent Orchestrator infrastructure."""

import sys
from pathlib import Path

# Add project root to Python path for src imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import aws_cdk as cdk  # noqa: E402
from stacks.api_stack import ApiStack  # noqa: E402
from stacks.metadata_stack import MetadataStack  # noqa: E402

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

# Deploy metadata stack (DynamoDB tables for custom agent metadata)
metadata_stack = MetadataStack(
    app,
    "AgentOrchestratorMetadata",
    env=env,
    description="DynamoDB tables for agent custom metadata and status tracking",
)

# Deploy API stack (Lambda + API Gateway)
api_stack = ApiStack(
    app,
    "AgentOrchestratorAPI",
    metadata_table=metadata_stack.metadata_table,
    status_table=metadata_stack.status_table,
    env=env,
    description="Lambda functions and API Gateway for agent registry",
)
api_stack.add_dependency(metadata_stack)

# Add tags to all resources
cdk.Tags.of(app).add("Project", "AgentOrchestrator")
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
