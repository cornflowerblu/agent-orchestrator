#!/usr/bin/env python3
"""Setup GitHub Actions OIDC provider and IAM role for AWS.

This script creates the AWS resources needed for GitHub Actions to authenticate
via OIDC (no long-lived credentials needed in GitHub).

Usage:
    # Make sure AWS credentials are configured locally
    aws sts get-caller-identity

    # Run the script
    python scripts/setup-github-oidc.py --account-id 123456789012 --repo owner/repo

    # Or use environment variables
    AWS_ACCOUNT_ID=123456789012 GITHUB_REPO=owner/repo python scripts/setup-github-oidc.py

After running:
    1. Add secret AWS_ROLE_ARN to your GitHub repository
    2. Add variable AWS_ACCOUNT_ID to your GitHub repository
    3. The CI workflow will now use OIDC authentication
"""

import argparse
import json
import os
import sys

try:
    import boto3
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


def setup_oidc_provider(iam_client, account_id: str) -> str:
    """Create or verify the GitHub OIDC provider exists."""
    oidc_url = "https://token.actions.githubusercontent.com"
    oidc_arn = f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"

    try:
        iam_client.get_open_id_connect_provider(OpenIDConnectProviderArn=oidc_arn)
        print(f"✓ OIDC provider already exists: {oidc_arn}")
        return oidc_arn
    except iam_client.exceptions.NoSuchEntityException:
        print("Creating OIDC provider...")
        response = iam_client.create_open_id_connect_provider(
            Url=oidc_url,
            ClientIDList=["sts.amazonaws.com"],
            # GitHub's OIDC thumbprint - NOTE: This thumbprint may become stale if GitHub
            # rotates their certificate. AWS now validates OIDC tokens without requiring
            # thumbprints for most providers, but we include it for compatibility.
            # If authentication fails, verify the current thumbprint at:
            # https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
            ThumbprintList=["6938fd4d98bab03faadb97b34396831e3780aea1"],
            Tags=[
                {"Key": "Purpose", "Value": "GitHub-Actions-OIDC"},
                {"Key": "ManagedBy", "Value": "setup-github-oidc-script"},
            ],
        )
        print(f"✓ Created OIDC provider: {response['OpenIDConnectProviderArn']}")
        return response["OpenIDConnectProviderArn"]


def setup_iam_role(iam_client, account_id: str, region: str, repo: str, oidc_arn: str) -> str:
    """Create or update the IAM role for GitHub Actions."""
    role_name = "GitHubActions-AgentFramework"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": oidc_arn},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {"token.actions.githubusercontent.com:sub": f"repo:{repo}:*"},
                },
            }
        ],
    }

    # SECURITY NOTE: These permissions are scoped for CDK deployments of the Agent Framework.
    # Broad permissions (e.g., cloudformation:*, apigateway:*) are required because CDK
    # generates dynamic resource names. Resource constraints are applied where possible.
    # Review and tighten these permissions based on your security requirements.
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                # CloudFormation needs broad access to manage stacks and resources.
                # Resource "*" is required because CDK creates resources with dynamic names.
                "Sid": "CloudFormationAccess",
                "Effect": "Allow",
                "Action": ["cloudformation:*"],
                "Resource": "*",
            },
            {
                # DynamoDB access is scoped to Agent* tables only.
                # This limits access to the specific tables used by this framework.
                "Sid": "DynamoDBAccess",
                "Effect": "Allow",
                "Action": ["dynamodb:*"],
                "Resource": [
                    f"arn:aws:dynamodb:{region}:{account_id}:table/AgentMetadata*",
                    f"arn:aws:dynamodb:{region}:{account_id}:table/AgentStatus*",
                ],
            },
            {
                # Lambda access for all functions in the account.
                # Consider scoping to specific function name patterns if possible.
                "Sid": "LambdaAccess",
                "Effect": "Allow",
                "Action": ["lambda:*"],
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:*",
            },
            {
                # API Gateway requires Resource "*" due to API ID being generated at deploy time.
                # This is a known CDK limitation for API Gateway deployments.
                "Sid": "APIGatewayAccess",
                "Effect": "Allow",
                "Action": ["apigateway:*"],
                "Resource": "*",
            },
            {
                # IAM permissions are scoped to AgentFramework* roles only.
                # PassRole is required for Lambda execution roles.
                "Sid": "IAMPassRole",
                "Effect": "Allow",
                "Action": [
                    "iam:PassRole",
                    "iam:GetRole",
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                ],
                "Resource": f"arn:aws:iam::{account_id}:role/AgentFramework*",
            },
            {
                # S3 access is scoped to CDK asset buckets only.
                # These buckets store deployment artifacts.
                "Sid": "S3Access",
                "Effect": "Allow",
                "Action": ["s3:*"],
                "Resource": [
                    f"arn:aws:s3:::cdk-*-assets-{account_id}-{region}",
                    f"arn:aws:s3:::cdk-*-assets-{account_id}-{region}/*",
                ],
            },
            {
                # SSM read-only access for CDK bootstrap parameters.
                "Sid": "SSMAccess",
                "Effect": "Allow",
                "Action": ["ssm:GetParameter"],
                "Resource": f"arn:aws:ssm:{region}:{account_id}:parameter/cdk-bootstrap/*",
            },
            {
                # ECR access is scoped to CDK repositories for container deployments.
                "Sid": "ECRAccess",
                "Effect": "Allow",
                "Action": ["ecr:*"],
                "Resource": f"arn:aws:ecr:{region}:{account_id}:repository/cdk-*",
            },
        ],
    }

    try:
        iam_client.get_role(RoleName=role_name)
        print(f"✓ IAM role already exists: {role_name}")
        iam_client.update_assume_role_policy(
            RoleName=role_name, PolicyDocument=json.dumps(trust_policy)
        )
        print("  Updated trust policy")
    except iam_client.exceptions.NoSuchEntityException:
        print(f"Creating IAM role: {role_name}")
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for GitHub Actions OIDC authentication",
            Tags=[
                {"Key": "Purpose", "Value": "GitHub-Actions-OIDC"},
                {"Key": "ManagedBy", "Value": "setup-github-oidc-script"},
            ],
        )
        print(f"✓ Created IAM role: {role_name}")

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="GitHubActionsPermissions",
        PolicyDocument=json.dumps(permissions_policy),
    )
    print("  Updated permissions policy")

    return f"arn:aws:iam::{account_id}:role/{role_name}"


def main():
    parser = argparse.ArgumentParser(
        description="Setup GitHub Actions OIDC provider and IAM role for AWS"
    )
    parser.add_argument(
        "--account-id",
        default=os.getenv("AWS_ACCOUNT_ID"),
        help="AWS Account ID (or set AWS_ACCOUNT_ID env var)",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS Region (default: us-east-1)",
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPO"),
        help="GitHub repository (owner/repo format, or set GITHUB_REPO env var)",
    )

    args = parser.parse_args()

    if not args.account_id:
        print("Error: --account-id is required (or set AWS_ACCOUNT_ID env var)")
        sys.exit(1)

    if not args.repo:
        print("Error: --repo is required (or set GITHUB_REPO env var)")
        sys.exit(1)

    print(f"\nSetting up GitHub Actions OIDC for:")
    print(f"  AWS Account: {args.account_id}")
    print(f"  AWS Region:  {args.region}")
    print(f"  GitHub Repo: {args.repo}")
    print()

    iam = boto3.client("iam")

    # Setup OIDC provider
    oidc_arn = setup_oidc_provider(iam, args.account_id)

    # Setup IAM role
    role_arn = setup_iam_role(iam, args.account_id, args.region, args.repo, oidc_arn)

    print()
    print("=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Add the following to your GitHub repository settings:")
    print()
    print("Secrets (Settings > Secrets and variables > Actions > Secrets):")
    print(f"  AWS_ROLE_ARN = {role_arn}")
    print()
    print("Variables (Settings > Secrets and variables > Actions > Variables):")
    print(f"  AWS_ACCOUNT_ID = {args.account_id}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
