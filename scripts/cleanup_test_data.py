#!/usr/bin/env python3
"""Cleanup test data from DynamoDB tables.

This script dynamically discovers all DynamoDB tables from CloudFormation
stacks prefixed with 'AgentOrchestrator' and deletes all items with a
'test-' prefix in their partition key.

Usage:
    python scripts/cleanup_test_data.py

Environment Variables:
    AWS_REGION: AWS region (default: us-east-1)
"""

import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError


def get_all_dynamodb_tables_from_stacks() -> list[str]:
    """Discover all DynamoDB tables from AgentOrchestrator CloudFormation stacks.

    Returns:
        List of DynamoDB table names (PhysicalResourceId)
    """
    cfn = boto3.client("cloudformation")
    tables = []

    try:
        # Get all stacks (paginate if needed)
        paginator = cfn.get_paginator("list_stacks")
        for page in paginator.paginate(StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE"]):
            for stack in page["StackSummaries"]:
                # Only process AgentOrchestrator stacks
                if stack["StackName"].startswith("AgentOrchestrator"):
                    print(f"  📦 Found stack: {stack['StackName']}")

                    # Get stack resources
                    try:
                        resource_paginator = cfn.get_paginator("list_stack_resources")
                        for resource_page in resource_paginator.paginate(
                            StackName=stack["StackName"]
                        ):
                            for resource in resource_page["StackResourceSummaries"]:
                                # Find DynamoDB tables
                                if resource["ResourceType"] == "AWS::DynamoDB::Table":
                                    table_name = resource["PhysicalResourceId"]
                                    tables.append(table_name)
                                    print(f"    └─ Table: {table_name}")
                    except ClientError as e:
                        print(f"    ⚠️  Could not list resources: {e}")
                        continue

    except ClientError as e:
        print(f"❌ Error listing stacks: {e}")
        sys.exit(1)

    return tables


def get_table_keys(table_name: str) -> tuple[str, str | None]:
    """Get partition key and sort key names for a table.

    Args:
        table_name: Name of the DynamoDB table

    Returns:
        Tuple of (partition_key_name, sort_key_name or None)
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Get key schema
    key_schema = table.key_schema
    partition_key = next(k["AttributeName"] for k in key_schema if k["KeyType"] == "HASH")
    sort_key = next((k["AttributeName"] for k in key_schema if k["KeyType"] == "RANGE"), None)

    return partition_key, sort_key


def cleanup_table(table_name: str, prefix: str = "test-") -> int:
    """Delete all items with given prefix from table.

    Args:
        table_name: Name of the DynamoDB table
        prefix: Prefix to match in partition key (default: 'test-')

    Returns:
        Number of items deleted
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        partition_key, sort_key = get_table_keys(table_name)
    except Exception as e:
        print(f"    ❌ Could not get table schema: {e}")
        return 0

    # Scan for items with prefix
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": f"begins_with({partition_key}, :prefix)",
        "ExpressionAttributeValues": {":prefix": prefix},
    }

    deleted = 0
    try:
        with table.batch_writer() as batch:
            while True:
                response = table.scan(**scan_kwargs)

                for item in response["Items"]:
                    # Build deletion key
                    key = {partition_key: item[partition_key]}
                    if sort_key:
                        key[sort_key] = item[sort_key]

                    batch.delete_item(Key=key)
                    deleted += 1

                # Check for more items
                if "LastEvaluatedKey" not in response:
                    break
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    except ClientError as e:
        print(f"    ❌ Error during cleanup: {e}")
        return deleted

    return deleted


def main() -> None:
    """Main entry point."""
    print("🔍 Discovering DynamoDB tables from CloudFormation stacks...")
    tables = get_all_dynamodb_tables_from_stacks()

    if not tables:
        print("⚠️  No DynamoDB tables found in AgentOrchestrator stacks")
        print("💡 Make sure stacks are deployed and named 'AgentOrchestrator*'")
        return

    print(f"\n📋 Found {len(tables)} table(s)")
    print()

    total_deleted = 0
    for table_name in tables:
        print(f"🧹 Cleaning {table_name}...", end=" ", flush=True)
        deleted = cleanup_table(table_name, prefix="test-")
        total_deleted += deleted
        if deleted > 0:
            print(f"✅ {deleted} item(s) deleted")
        else:
            print("✅ No test items found")

    print()
    print(f"✅ Cleanup complete: {total_deleted} total item(s) deleted from {len(tables)} table(s)")


if __name__ == "__main__":
    main()
