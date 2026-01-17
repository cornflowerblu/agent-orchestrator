"""CDK stack for Loop Framework infrastructure with Cedar policies.

Task T122: Create infrastructure/cdk/stacks/loop_stack.py for Cedar policies
"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class LoopStack(Stack):
    """Stack for the Loop Framework infrastructure.

    Creates:
    - Cedar policy engine for iteration limits (AgentCore Policy)
    - IAM roles for loop execution
    - CloudWatch log groups for loop observability
    - Lambda function for policy enforcement

    Task T122: Create infrastructure/cdk/stacks/loop_stack.py for Cedar policies
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        """Initialize the Loop stack.

        Args:
            scope: CDK scope
            construct_id: Unique ID for this construct
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        # CloudWatch Log Group for loop observability
        loop_log_group = logs.LogGroup(
            self,
            "LoopObservabilityLogs",
            log_group_name="/aws/bedrock/agent-loops",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,  # Delete logs on stack destroy
        )

        # IAM role for loop framework execution
        loop_execution_role = iam.Role(
            self,
            "LoopExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Loop Framework agents",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant permissions for AgentCore services
        loop_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # AgentCore Memory for checkpoints
                    "bedrock:CreateMemory",
                    "bedrock:GetMemory",
                    "bedrock:PutMemoryItem",
                    "bedrock:GetMemoryItem",
                    "bedrock:ListMemoryItems",
                    # AgentCore Policy for iteration limits
                    "bedrock:CreatePolicyEngine",
                    "bedrock:GetPolicyEngine",
                    "bedrock:CreatePolicy",
                    "bedrock:GetPolicy",
                    "bedrock:EvaluatePolicy",
                    # AgentCore Gateway for tool discovery
                    "bedrock:ListGatewayTools",
                    "bedrock:InvokeGatewayTool",
                    # Code Interpreter for verification
                    "bedrock:CreateCodeInterpreterSession",
                    "bedrock:ExecuteCode",
                ],
                resources=["*"],  # Scope to specific resources in production
            )
        )

        # Grant permissions for Observability (CloudWatch and X-Ray)
        loop_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:StartQuery",
                    "logs:GetQueryResults",
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetTraceSummaries",
                    "xray:GetServiceGraph",
                ],
                resources=[
                    loop_log_group.log_group_arn,
                    f"{loop_log_group.log_group_arn}:*",
                ],
            )
        )

        # Lambda function for Policy enforcer (monitoring component)
        policy_enforcer_lambda = lambda_.Function(
            self,
            "PolicyEnforcerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="policy_enforcer.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=loop_execution_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "LOG_GROUP_NAME": loop_log_group.log_group_name,
                "POLICY_ENGINE_NAME": "LoopIterationPolicyEngine",
            },
            description="Policy enforcer for monitoring loop iterations",
        )

        # Store outputs for cross-stack references
        self.loop_execution_role = loop_execution_role
        self.loop_log_group = loop_log_group
        self.policy_enforcer_lambda = policy_enforcer_lambda

        # CloudFormation outputs
        CfnOutput(
            self,
            "LoopExecutionRoleArn",
            value=loop_execution_role.role_arn,
            description="ARN of the Loop Framework execution role",
            export_name=f"{construct_id}-ExecutionRoleArn",
        )

        CfnOutput(
            self,
            "LoopLogGroupName",
            value=loop_log_group.log_group_name,
            description="CloudWatch Log Group for loop observability",
            export_name=f"{construct_id}-LogGroupName",
        )

        CfnOutput(
            self,
            "PolicyEnforcerLambdaArn",
            value=policy_enforcer_lambda.function_arn,
            description="ARN of the Policy Enforcer Lambda function",
            export_name=f"{construct_id}-PolicyEnforcerArn",
        )
