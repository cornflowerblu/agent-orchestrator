# Quickstart: Agent Framework

**Feature**: 001-agent-framework
**Date**: 2026-01-16

## Prerequisites

- AWS Account with Bedrock AgentCore access
- Python 3.11+
- AWS CLI configured with appropriate credentials
- Node.js 24+ (LTS, for CDK)

## Environment Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install \
  bedrock-agentcore-sdk-python \
  strands \
  boto3 \
  pydantic \
  pytest \
  pytest-asyncio \
  pytest-cov \
  moto

# Install CDK (for infrastructure)
npm install -g aws-cdk
```

### 2. AWS Configuration

```bash
# Ensure AWS credentials are configured
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### 3. Environment Variables

Create `.env` file (do not commit):

```bash
AWS_REGION=us-east-1
AGENT_METADATA_TABLE=AgentMetadata
AGENT_STATUS_TABLE=AgentStatus
GATEWAY_URL=https://your-gateway-endpoint/mcp
```

## Quick Verification

### Test Agent Card Schema

```bash
# Validate an Agent Card against schema
python -c "
import json
from jsonschema import validate

with open('specs/001-agent-framework/contracts/agent-card.schema.json') as f:
    schema = json.load(f)

sample_card = {
    'name': 'test-agent',
    'description': 'A test agent for verification',
    'version': '1.0.0',
    'url': 'https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/test/invocations/',
    'protocolVersion': '0.3.0',
    'preferredTransport': 'JSONRPC',
    'capabilities': {'streaming': False},
    'defaultInputModes': ['text'],
    'defaultOutputModes': ['text'],
    'skills': [
        {'id': 'test-skill', 'name': 'Test Skill', 'description': 'A skill for testing purposes', 'tags': ['test']}
    ]
}

validate(sample_card, schema)
print('✓ Agent Card schema valid')
"
```

### Test Custom Metadata Schema

```bash
python -c "
import json
from jsonschema import validate

with open('specs/001-agent-framework/contracts/custom-metadata.schema.json') as f:
    schema = json.load(f)

sample_metadata = {
    'agent_name': 'test-agent',
    'version': '1.0.0',
    'input_schemas': [
        {'name': 'source-code', 'semantic_type': 'artifact', 'description': 'Source code to process', 'required': True}
    ],
    'output_schemas': [
        {'name': 'analysis-report', 'semantic_type': 'document', 'description': 'Analysis results', 'guaranteed': True}
    ],
    'consultation_requirements': []
}

validate(sample_metadata, schema)
print('✓ Custom Metadata schema valid')
"
```

## Development Workflow

### 1. Define an Agent

Create an Agent Card JSON file:

```json
// src/agents/manifests/my-agent.json
{
  "name": "my-agent",
  "description": "My custom agent for the platform",
  "version": "1.0.0",
  "url": "${RUNTIME_URL}",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "capabilities": {
    "streaming": true
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    {
      "id": "my-skill",
      "name": "My Skill",
      "description": "What my agent can do",
      "tags": ["custom"]
    }
  ]
}
```

### 2. Implement Agent Logic

```python
# src/agents/my_agent.py
from bedrock_agentcore.runtime import Runtime, InvocationContext, InvocationResponse

app = Runtime()

@app.entrypoint
async def handle_request(context: InvocationContext) -> InvocationResponse:
    """Main entry point for agent invocations."""
    input_text = context.input.get("inputText", "")

    # Your agent logic here
    response_text = f"Processed: {input_text}"

    return InvocationResponse(
        output={
            "message": {
                "content": [{"type": "text", "text": response_text}]
            }
        }
    )
```

### 3. Add Custom Metadata

```python
# scripts/register_metadata.py
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('AgentMetadata')

metadata = {
    'agent_name': 'my-agent',
    'version': '1.0.0',
    'input_schemas': [
        {
            'name': 'user-request',
            'semantic_type': 'document',
            'description': 'User request to process',
            'required': True
        }
    ],
    'output_schemas': [
        {
            'name': 'response',
            'semantic_type': 'document',
            'description': 'Agent response',
            'guaranteed': True
        }
    ],
    'consultation_requirements': [],
    'created_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
}

table.put_item(Item=metadata)
print(f"✓ Registered metadata for {metadata['agent_name']}")
```

### 4. Deploy Agent

```bash
# Deploy using AgentCore CLI (from bedrock-agentcore-starter-toolkit)
agentcore deploy --manifest src/agents/manifests/my-agent.json

# Or deploy infrastructure with CDK
cd infrastructure/cdk
cdk deploy
```

### 5. Run Tests

```bash
# Unit + contract tests (fast, no AWS needed)
pytest tests/unit tests/contract -v

# With coverage (mirrors CI)
pytest tests/unit tests/contract \
  --cov=src --cov-report=html --cov-report=term \
  --cov-fail-under=80

# View coverage report
open htmlcov/index.html  # macOS
# xdg-open htmlcov/index.html  # Linux

# Integration tests (requires AWS credentials)
pytest tests/integration/ -v --tb=short
```

### 6. CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every PR:

1. **Unit + Contract tests** with 80% coverage threshold
2. **AWS Integration tests** (deploys test stack, runs tests, tears down)
3. **PR comment** with test results summary

PRs cannot merge until all checks pass. See `specs/001-agent-framework/research.md` for the full workflow definition.

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/agents/base_agent.py` | Base class for all agents |
| `src/agents/manifests/*.json` | Agent Card definitions |
| `src/metadata/models.py` | Pydantic models for metadata |
| `src/metadata/storage.py` | DynamoDB operations |
| `src/consultation/rules.py` | Consultation rule definitions |
| `src/registry/handlers.py` | API Lambda handlers |
| `infrastructure/cdk/app.py` | CDK infrastructure |

## Common Tasks

### Query Agents by Skill

```python
from src.registry.query import AgentRegistry

registry = AgentRegistry()
agents = registry.find_by_skill('code-review')
for agent in agents:
    print(f"  {agent.name} - {agent.status}")
```

### Check Consultation Requirements

```python
from src.consultation.enforcement import ConsultationEngine
from src.consultation.rules import ConsultationRequirement, ConsultationPhase

# Create engine with requirements
requirements = [
    ConsultationRequirement(
        agent_name="security-agent",
        phase=ConsultationPhase.PRE_COMPLETION,
        mandatory=True
    )
]
engine = ConsultationEngine(requirements=requirements)

# Get requirements for a specific phase
pre_completion_reqs = engine.get_requirements(ConsultationPhase.PRE_COMPLETION)
for req in pre_completion_reqs:
    print(f"  Must consult: {req.agent_name} ({req.phase.value})")
```

### Validate Task Assignment

```python
from src.registry.query import AgentRegistry

registry = AgentRegistry()
result = registry.check_compatibility(
    agent_name='development-agent',
    required_skill='code-implementation',
    available_inputs=[
        {'name': 'technical-specification', 'semantic_type': 'document'}
    ]
)
print(f"Compatible: {result.compatible}")
if not result.compatible:
    print(f"Reasons: {result.reasons}")
```

## Troubleshooting

### Agent Card Not Found

```bash
# Verify agent is deployed
curl https://your-agent-url/.well-known/agent-card.json

# Check AgentCore Runtime status
aws bedrock-agentcore list-agent-runtimes --region us-east-1
```

### Gateway Tool Discovery Fails

```bash
# Test Gateway connectivity
python -c "
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

url = 'https://your-gateway-endpoint/mcp'
token = 'your-access-token'

client = MCPClient(lambda: streamablehttp_client(url, headers={'Authorization': f'Bearer {token}'}))
with client:
    tools = client.list_tools_sync()
    print(f'Found {len(tools)} tools')
"
```

### DynamoDB Access Issues

```bash
# Verify table exists
aws dynamodb describe-table --table-name AgentMetadata --region us-east-1

# Check IAM permissions
aws sts get-caller-identity
```

## Next Steps

1. Review `data-model.md` for entity details
2. Review `contracts/` for API specifications
3. Run `/speckit.tasks` to generate implementation tasks
4. Begin implementation with `/speckit.implement`
