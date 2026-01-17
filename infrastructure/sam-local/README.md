# SAM Local Testing with LocalStack

Run Lambda functions locally in Docker containers against LocalStack.

## Prerequisites

- Docker running
- AWS SAM CLI installed (`brew install aws-sam-cli`)

## Quick Start

```bash
cd infrastructure/sam-local

# 1. Build Lambda packages (installs deps for Linux/Python 3.11)
./build.sh

# 2. Start LocalStack (creates tables and log groups automatically)
docker-compose up -d

# 3. Test!
sam local invoke ListAgentsFunction -e events/list_agents.json
sam local invoke ToolRegistryFunction -e events/tool_registry_list.json
```

## What Gets Created

The `init-localstack.sh` script automatically creates:

**DynamoDB Tables:**
- `AgentMetadata` (with SkillIndex GSI)
- `AgentStatus`
- `LoopCheckpoints`

**CloudWatch Log Groups:**
- `/aws/bedrock/agent-gateway`
- `/aws/bedrock/agent-loops`

## Commands

### Build Lambda packages
```bash
./build.sh
```
This installs dependencies for Linux x86_64 / Python 3.11 (matching Lambda runtime).

### Start LocalStack
```bash
docker-compose up -d
```

### Stop LocalStack
```bash
docker-compose down
```

### Stop and remove data
```bash
docker-compose down -v
```

### Check LocalStack is ready
```bash
curl http://localhost:4566/_localstack/health
```

### Invoke Lambda functions
```bash
# API handlers
sam local invoke ListAgentsFunction -e events/list_agents.json
sam local invoke GetAgentFunction -e events/get_agent.json
sam local invoke UpdateMetadataFunction -e events/update_metadata.json
sam local invoke CheckCompatibilityFunction -e events/check_compatibility.json
sam local invoke UpdateStatusFunction -e events/update_status.json

# Standalone handlers
sam local invoke ToolRegistryFunction -e events/tool_registry_list.json
sam local invoke PolicyEnforcerFunction -e events/policy_enforcer.json
```

### Seed test data
```bash
# Add a test agent to DynamoDB
aws --endpoint-url=http://localhost:4566 dynamodb put-item \
  --table-name AgentMetadata \
  --item '{
    "agent_name": {"S": "test-agent"},
    "version": {"S": "1.0.0"},
    "input_schemas": {"L": []},
    "output_schemas": {"L": []},
    "consultation_requirements": {"L": []},
    "created_at": {"S": "2024-01-01T00:00:00Z"},
    "updated_at": {"S": "2024-01-01T00:00:00Z"}
  }'

# Verify it was created
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name AgentMetadata
```

## Event Files

| File | Handler | Description |
|------|---------|-------------|
| `list_agents.json` | ListAgentsFunction | GET /agents |
| `get_agent.json` | GetAgentFunction | GET /agents/{name} |
| `update_metadata.json` | UpdateMetadataFunction | PUT /agents/{name}/metadata |
| `check_compatibility.json` | CheckCompatibilityFunction | POST /agents/compatibility |
| `update_status.json` | UpdateStatusFunction | PUT /agents/{name}/status |
| `tool_registry_list.json` | ToolRegistryFunction | List tools |
| `tool_registry_register.json` | ToolRegistryFunction | Register a tool |
| `policy_enforcer.json` | PolicyEnforcerFunction | Check loop policy |

## Debugging

```bash
# Verbose SAM output
sam local invoke ListAgentsFunction -e events/list_agents.json --debug

# Check LocalStack logs
docker-compose logs -f localstack

# Query DynamoDB directly
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name AgentMetadata

# Check CloudWatch logs
aws --endpoint-url=http://localhost:4566 logs describe-log-groups
```

## Troubleshooting

**"Could not connect to the endpoint URL"**
- Make sure LocalStack is running: `docker-compose ps`
- Check health: `curl http://localhost:4566/_localstack/health`

**"No module named 'pydantic'"**
- Run `./build.sh` to install dependencies

**"No module named 'pydantic_core._pydantic_core'"**
- The build script installs Linux x86_64 / Python 3.11 binaries
- Make sure you ran `./build.sh` (not `sam build`)

**Lambda can't reach LocalStack**
- The template uses `host.docker.internal:4566` which works on Mac/Windows
- On Linux, you may need `--network host` flag

## What This Tests

- Lambda handler imports work correctly
- Dependencies are available (pydantic, boto3, etc.)
- Handler logic executes without errors
- DynamoDB read/write operations work
- CloudWatch logging works
- API Gateway event parsing works
- Response format is correct
