#!/bin/bash
# Initialize LocalStack resources for SAM local testing

echo "Creating DynamoDB tables..."

# AgentMetadata table
awslocal dynamodb create-table \
  --table-name AgentMetadata \
  --attribute-definitions \
    AttributeName=agent_name,AttributeType=S \
    AttributeName=skill_id,AttributeType=S \
  --key-schema AttributeName=agent_name,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[
    {
      "IndexName": "SkillIndex",
      "KeySchema": [{"AttributeName": "skill_id", "KeyType": "HASH"}],
      "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["agent_name", "version"]}
    }
  ]'

# AgentStatus table
awslocal dynamodb create-table \
  --table-name AgentStatus \
  --attribute-definitions AttributeName=agent_name,AttributeType=S \
  --key-schema AttributeName=agent_name,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# LoopCheckpoints table
awslocal dynamodb create-table \
  --table-name LoopCheckpoints \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=iteration,AttributeType=N \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
    AttributeName=iteration,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

echo "Creating CloudWatch Log groups..."

# Log groups for standalone handlers
awslocal logs create-log-group --log-group-name /aws/bedrock/agent-gateway
awslocal logs create-log-group --log-group-name /aws/bedrock/agent-loops

# Create log streams
awslocal logs create-log-stream \
  --log-group-name /aws/bedrock/agent-gateway \
  --log-stream-name gateway-AgentOrchestratorGateway

awslocal logs create-log-stream \
  --log-group-name /aws/bedrock/agent-loops \
  --log-stream-name loop-test-loop-123

echo "LocalStack initialization complete!"
