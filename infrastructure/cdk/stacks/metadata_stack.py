"""CDK stack for agent metadata and status DynamoDB tables."""

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class MetadataStack(cdk.Stack):
    """
    Stack containing DynamoDB tables for agent custom metadata and status tracking.

    Tables:
    - AgentMetadata: Stores custom agent metadata (inputs, outputs, consultation requirements)
    - AgentStatus: Tracks agent runtime status for scheduling decisions
    - LoopCheckpoints: Stores loop framework checkpoint state for recovery
    """

    def __init__(
        self, scope: Construct, construct_id: str, environment: str = "development", **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Determine removal policy based on environment
        # RETAIN for production (prevent accidental data loss)
        # DESTROY for non-prod (enable full cleanup in CI/CD)
        is_production = environment.lower() == "production"
        metadata_removal_policy = (
            cdk.RemovalPolicy.RETAIN if is_production else cdk.RemovalPolicy.DESTROY
        )

        # AgentMetadata Table
        self.metadata_table = dynamodb.Table(
            self,
            "AgentMetadata",
            table_name="AgentMetadata",
            partition_key=dynamodb.Attribute(name="agent_name", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=metadata_removal_policy,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # GSI for skill-based lookups
        self.metadata_table.add_global_secondary_index(
            index_name="SkillIndex",
            partition_key=dynamodb.Attribute(name="skill_id", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.INCLUDE,
            non_key_attributes=["agent_name", "version"],
        )

        # AgentStatus Table
        self.status_table = dynamodb.Table(
            self,
            "AgentStatus",
            table_name="AgentStatus",
            partition_key=dynamodb.Attribute(name="agent_name", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            time_to_live_attribute="ttl",  # Auto-cleanup stale status records
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Safe to recreate
        )

        # LoopCheckpoints Table
        self.checkpoints_table = dynamodb.Table(
            self,
            "LoopCheckpoints",
            table_name="LoopCheckpoints",
            partition_key=dynamodb.Attribute(name="session_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="iteration", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=is_production,  # Enable PITR for production
            removal_policy=metadata_removal_policy,  # Same as metadata (RETAIN/DESTROY based on env)
        )

        # Outputs
        cdk.CfnOutput(
            self,
            "MetadataTableName",
            value=self.metadata_table.table_name,
            description="DynamoDB table for agent custom metadata",
            export_name="AgentMetadataTableName",
        )

        cdk.CfnOutput(
            self,
            "MetadataTableArn",
            value=self.metadata_table.table_arn,
            description="ARN of agent metadata table",
            export_name="AgentMetadataTableArn",
        )

        cdk.CfnOutput(
            self,
            "StatusTableName",
            value=self.status_table.table_name,
            description="DynamoDB table for agent status tracking",
            export_name="AgentStatusTableName",
        )

        cdk.CfnOutput(
            self,
            "StatusTableArn",
            value=self.status_table.table_arn,
            description="ARN of agent status table",
            export_name="AgentStatusTableArn",
        )

        cdk.CfnOutput(
            self,
            "CheckpointsTableName",
            value=self.checkpoints_table.table_name,
            description="DynamoDB table for loop framework checkpoints",
            export_name="LoopCheckpointsTableName",
        )

        cdk.CfnOutput(
            self,
            "CheckpointsTableArn",
            value=self.checkpoints_table.table_arn,
            description="ARN of loop checkpoints table",
            export_name="LoopCheckpointsTableArn",
        )
