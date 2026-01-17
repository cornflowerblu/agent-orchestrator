#!/usr/bin/env python3
"""AWS CDK app entry point for Agent Orchestrator infrastructure."""

import os
import sys
from pathlib import Path

# Add project root to Python path for src imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import aws_cdk as cdk  # noqa: E402
from stacks.api_stack import ApiStack  # noqa: E402
from stacks.gateway_stack import GatewayStack  # noqa: E402
from stacks.loop_stack import LoopStack  # noqa: E402
from stacks.metadata_stack import MetadataStack  # noqa: E402

app = cdk.App()

# Determine environment (priority: env var > CI detection > CDK context > default)
environment = (
    os.getenv("ENVIRONMENT")  # Explicit override
    or ("ci" if os.getenv("GITHUB_ACTIONS") else None)  # Auto-detect CI
    or app.node.try_get_context("environment")  # CDK context
    or "development"  # Safe default
)

print(f"🌍 Deploying to environment: {environment}")

# Determine stack name prefix based on environment
# Production: Use standard names (AgentOrchestratorMetadata)
# Non-production: Include branch name for isolation (AgentOrchestrator-feat-xyz-Metadata)
if environment == "production":
    stack_prefix = "AgentOrchestrator"
else:
    # Get branch name from CI environment (GitHub Actions sets GITHUB_REF_NAME)
    # Format: refs/heads/feature-branch → feature-branch
    # Sanitize for CloudFormation (alphanumeric and hyphens only, max 20 chars)
    branch = os.getenv("GITHUB_REF_NAME", "dev")
    branch = branch.replace("/", "-").replace("_", "-")[:20]
    # Remove any invalid characters
    branch = "".join(c for c in branch if c.isalnum() or c == "-")
    stack_prefix = f"AgentOrchestrator-{branch}-"
    print(f"📦 Using isolated stack prefix: {stack_prefix}")

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

# Deploy metadata stack (DynamoDB tables for custom agent metadata)
metadata_stack = MetadataStack(
    app,
    f"{stack_prefix}Metadata",
    environment=environment,
    env=env,
    description="DynamoDB tables for agent custom metadata and status tracking",
)

# Deploy API stack (Lambda + API Gateway)
api_stack = ApiStack(
    app,
    f"{stack_prefix}API",
    metadata_table=metadata_stack.metadata_table,
    status_table=metadata_stack.status_table,
    env=env,
    description="Lambda functions and API Gateway for agent registry",
)
api_stack.add_dependency(metadata_stack)

# Deploy Loop stack (Loop Framework with Cedar policies)
loop_stack = LoopStack(
    app,
    f"{stack_prefix}Loop",
    env=env,
    description="Loop Framework infrastructure with Cedar policy engine",
)
# Loop stack is independent, no dependencies needed

# Deploy Gateway stack (AgentCore Gateway for tool discovery)
gateway_stack = GatewayStack(
    app,
    f"{stack_prefix}Gateway",
    env=env,
    description="AgentCore Gateway infrastructure for tool discovery and invocation",
)
# Gateway stack is independent, no dependencies needed

# Add tags to all resources
cdk.Tags.of(app).add("Project", "AgentOrchestrator")
cdk.Tags.of(app).add("ManagedBy", "CDK")
cdk.Tags.of(app).add("Environment", environment)

app.synth()
