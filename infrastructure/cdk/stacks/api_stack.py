"""CDK stack for Registry API with Lambda and API Gateway.

Task T075: Create API stack with Lambda + API Gateway
"""

from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    Stack,
)
from aws_cdk import (
    aws_apigateway as apigw,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from constructs import Construct


class ApiStack(Stack):
    """Stack for the Registry API.

    Creates:
    - Lambda functions for each API handler
    - API Gateway REST API
    - IAM roles with appropriate permissions
    - CloudWatch log groups

    Task T075: Create API stack with Lambda + API Gateway
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        metadata_table: dynamodb.ITable,
        status_table: dynamodb.ITable,
        **kwargs,
    ) -> None:
        """Initialize the API stack.

        Args:
            scope: CDK scope
            construct_id: Unique ID for this construct
            metadata_table: DynamoDB table for agent metadata
            status_table: DynamoDB table for agent status
            **kwargs: Additional stack props
        """
        super().__init__(scope, construct_id, **kwargs)

        # Lambda execution role
        lambda_role = iam.Role(
            self,
            "RegistryLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Grant table permissions
        metadata_table.grant_read_write_data(lambda_role)
        status_table.grant_read_write_data(lambda_role)

        # Common Lambda environment variables
        lambda_env = {
            "AGENT_METADATA_TABLE": metadata_table.table_name,
            "AGENT_STATUS_TABLE": status_table.table_name,
            "LOG_LEVEL": "INFO",
        }

        # Shared code asset for all API Lambdas
        # Bundle project root with src/ directory structure and install dependencies
        api_code = lambda_.Code.from_asset(
            "../..",
            exclude=[
                ".venv",
                ".venv/**",
                "*.pyc",
                "__pycache__",
                "__pycache__/**",
                ".pytest_cache",
                ".pytest_cache/**",
                ".coverage",
                ".git",
                ".git/**",
                ".gitignore",
                ".ruff_cache",
                ".ruff_cache/**",
                "*.egg-info",
                "*.egg-info/**",
                "tests",
                "tests/**",
                "infrastructure",
                "infrastructure/**",
                ".specify",
                ".specify/**",
                ".claude",
                ".claude/**",
                "*.md",
                ".env",
                ".DS_Store",
                "node_modules",
                "node_modules/**",
                "cdk.out",
                "cdk.out/**",
                ".mypy_cache",
                ".mypy_cache/**",
                "*.egg",
                "build",
                "build/**",
                "dist",
                "dist/**",
            ],
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                command=[
                    "bash",
                    "-c",
                    # Install pydantic with correct platform for Lambda (x86_64 Linux)
                    "pip install pydantic --platform manylinux2014_x86_64 "
                    "--only-binary=:all: -t /asset-output && "
                    "cp -r /asset-input/src /asset-output/",
                ],
            ),
        )

        # Create Lambda layer for dependencies
        # Note: In production, create a layer with dependencies
        lambda_props = {
            "runtime": lambda_.Runtime.PYTHON_3_11,
            "role": lambda_role,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "tracing": lambda_.Tracing.ACTIVE,  # Enable X-Ray tracing
            "environment": lambda_env,
        }

        # List Agents Handler (T076)
        list_agents_fn = lambda_.Function(
            self,
            "ListAgentsFunction",
            code=api_code,
            handler="src.registry.handlers.list_agents_handler",
            **lambda_props,
        )

        # Get Agent Handler (T077)
        get_agent_fn = lambda_.Function(
            self,
            "GetAgentFunction",
            code=api_code,
            handler="src.registry.handlers.get_agent_handler",
            **lambda_props,
        )

        # Update Agent Metadata Handler (T078)
        update_metadata_fn = lambda_.Function(
            self,
            "UpdateMetadataFunction",
            code=api_code,
            handler="src.registry.handlers.update_agent_metadata_handler",
            **lambda_props,
        )

        # Get Consultation Requirements Handler (T079)
        get_consultation_fn = lambda_.Function(
            self,
            "GetConsultationFunction",
            code=api_code,
            handler="src.registry.handlers.get_consultation_requirements_handler",
            **lambda_props,
        )

        # Check Compatibility Handler (T080)
        check_compat_fn = lambda_.Function(
            self,
            "CheckCompatibilityFunction",
            code=api_code,
            handler="src.registry.handlers.check_compatibility_handler",
            **lambda_props,
        )

        # Find Compatible Agents Handler (T081)
        find_compat_fn = lambda_.Function(
            self,
            "FindCompatibleFunction",
            code=api_code,
            handler="src.registry.handlers.find_compatible_agents_handler",
            **lambda_props,
        )

        # Get Agent Status Handler (T082)
        get_status_fn = lambda_.Function(
            self,
            "GetStatusFunction",
            code=api_code,
            handler="src.registry.handlers.get_agent_status_handler",
            **lambda_props,
        )

        # Update Agent Status Handler (T083)
        update_status_fn = lambda_.Function(
            self,
            "UpdateStatusFunction",
            code=api_code,
            handler="src.registry.handlers.update_agent_status_handler",
            **lambda_props,
        )

        # Create API Gateway
        api = apigw.RestApi(
            self,
            "RegistryApi",
            rest_api_name="Agent Registry API",
            description="API for agent discovery and registry",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
            deploy_options=apigw.StageOptions(
                stage_name="v1",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                tracing_enabled=True,  # Enable X-Ray tracing
            ),
        )

        # Create API resources and methods
        agents = api.root.add_resource("agents")

        # GET /agents - List all agents
        agents.add_method(
            "GET",
            apigw.LambdaIntegration(list_agents_fn),
        )

        # POST /agents/compatibility - Check compatibility
        compatibility = agents.add_resource("compatibility")
        compatibility.add_method(
            "POST",
            apigw.LambdaIntegration(check_compat_fn),
        )

        # POST /agents/find-compatible - Find compatible agents
        find_compatible = agents.add_resource("find-compatible")
        find_compatible.add_method(
            "POST",
            apigw.LambdaIntegration(find_compat_fn),
        )

        # /agents/{agent_name}
        agent = agents.add_resource("{agent_name}")

        # GET /agents/{agent_name} - Get agent
        agent.add_method(
            "GET",
            apigw.LambdaIntegration(get_agent_fn),
        )

        # /agents/{agent_name}/metadata
        metadata = agent.add_resource("metadata")

        # PUT /agents/{agent_name}/metadata - Update metadata
        metadata.add_method(
            "PUT",
            apigw.LambdaIntegration(update_metadata_fn),
        )

        # /agents/{agent_name}/consultation-requirements
        consultation = agent.add_resource("consultation-requirements")

        # GET /agents/{agent_name}/consultation-requirements
        consultation.add_method(
            "GET",
            apigw.LambdaIntegration(get_consultation_fn),
        )

        # /agents/{agent_name}/status
        status = agent.add_resource("status")

        # GET /agents/{agent_name}/status - Get status
        status.add_method(
            "GET",
            apigw.LambdaIntegration(get_status_fn),
        )

        # PUT /agents/{agent_name}/status - Update status
        status.add_method(
            "PUT",
            apigw.LambdaIntegration(update_status_fn),
        )

        # Store references
        self.api = api
        self.list_agents_fn = list_agents_fn
        self.get_agent_fn = get_agent_fn
        self.update_metadata_fn = update_metadata_fn
        self.get_consultation_fn = get_consultation_fn
        self.check_compat_fn = check_compat_fn
        self.find_compat_fn = find_compat_fn
        self.get_status_fn = get_status_fn
        self.update_status_fn = update_status_fn

        # Export API URL for integration tests
        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="API Gateway URL for integration tests",
            export_name=f"{construct_id}-ApiUrl",
        )
