"""CDK stack for AgentCore Gateway infrastructure.

This stack creates the infrastructure needed for AgentCore Gateway tool discovery
and invocation, including IAM roles, CloudWatch logging, and Lambda functions.
"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class GatewayStack(Stack):
    """Stack for AgentCore Gateway infrastructure.

    Creates:
    - IAM roles for Gateway access
    - CloudWatch log groups for Gateway observability
    - Lambda function for tool registration
    - Gateway service configuration
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        """Initialize the Gateway stack.

        Args:
            scope: CDK scope
            construct_id: Unique ID for this construct
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        # CloudWatch Log Group for Gateway observability
        gateway_log_group = logs.LogGroup(
            self,
            "GatewayObservabilityLogs",
            log_group_name="/aws/bedrock/agent-gateway",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,  # Delete logs on stack destroy
        )

        # IAM role for Gateway service execution
        gateway_execution_role = iam.Role(
            self,
            "GatewayExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for AgentCore Gateway service",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant permissions for AgentCore Gateway services
        gateway_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # AgentCore Gateway for tool discovery and invocation
                    "bedrock:CreateGateway",
                    "bedrock:GetGateway",
                    "bedrock:ListGateways",
                    "bedrock:DeleteGateway",
                    "bedrock:RegisterTool",
                    "bedrock:UnregisterTool",
                    "bedrock:ListTools",
                    "bedrock:InvokeTool",
                    "bedrock:SearchTools",
                    # AgentCore Memory for tool metadata
                    "bedrock:CreateMemory",
                    "bedrock:GetMemory",
                    "bedrock:PutMemoryItem",
                    "bedrock:GetMemoryItem",
                    "bedrock:ListMemoryItems",
                ],
                resources=["*"],  # Scope to specific resources in production
            )
        )

        # Grant permissions for Observability (CloudWatch and X-Ray)
        gateway_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=[
                    gateway_log_group.log_group_arn,
                    f"{gateway_log_group.log_group_arn}:*",
                ],
            )
        )

        # Lambda function for tool registration
        tool_registry_lambda = lambda_.Function(
            self,
            "ToolRegistryFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="tool_registry.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=gateway_execution_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "LOG_GROUP_NAME": gateway_log_group.log_group_name,
                "GATEWAY_NAME": "AgentOrchestratorGateway",
            },
            description="Tool registration handler for AgentCore Gateway",
        )

        # Store outputs for cross-stack references
        self.gateway_execution_role = gateway_execution_role
        self.gateway_log_group = gateway_log_group
        self.tool_registry_lambda = tool_registry_lambda

        # CloudFormation outputs
        CfnOutput(
            self,
            "GatewayExecutionRoleArn",
            value=gateway_execution_role.role_arn,
            description="ARN of the Gateway execution role",
            export_name=f"{construct_id}-ExecutionRoleArn",
        )

        CfnOutput(
            self,
            "GatewayLogGroupName",
            value=gateway_log_group.log_group_name,
            description="CloudWatch Log Group for Gateway observability",
            export_name=f"{construct_id}-LogGroupName",
        )

        CfnOutput(
            self,
            "ToolRegistryLambdaArn",
            value=tool_registry_lambda.function_arn,
            description="ARN of the Tool Registry Lambda function",
            export_name=f"{construct_id}-ToolRegistryArn",
        )
