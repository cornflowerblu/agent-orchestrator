# Testing Workflow

This document describes the testing strategy for the agent-orchestrator project.

## Overview

The project uses a **three-tier testing strategy**:

```
┌─────────────────────┬──────────────┬────────────────────────────────────┐
│ Tier                │ Speed        │ Environment                        │
├─────────────────────┼──────────────┼────────────────────────────────────┤
│ Unit Tests          │ Fastest      │ Mocked (no AWS)                    │
│ SAM Local           │ ~60s         │ LocalStack + Docker                │
│ Integration (E2E)   │ Minutes      │ Real AWS (deployed infrastructure) │
└─────────────────────┴──────────────┴────────────────────────────────────┘
```

### Why Three Tiers?

1. **Unit Tests** - Fast feedback on logic with mocked dependencies
2. **SAM Local** - Pre-deploy gate that catches packaging/config issues
3. **E2E Integration** - Validates real AWS behavior with deployed infrastructure

## Test Tiers

### 1. Unit Tests (`-m unit`)

Fast, isolated tests with mocked dependencies.

```bash
pytest -m unit -v
pytest -m unit --cov=src --cov-fail-under=80
```

**Location**: `tests/unit/`

### 2. SAM Local Tests (`-m sam_local`)

**Pre-deploy sanity tests** that invoke actual Lambda functions via `sam local invoke`, hitting LocalStack for DynamoDB.

These catch issues that mocked tests miss:
- Lambda handler entry point typos
- Missing imports in packaged Lambda
- Environment variable misconfiguration
- DynamoDB API differences (moto vs real)
- Cold start issues

```bash
# Start LocalStack first
docker-compose -f infrastructure/sam-local/docker-compose.yml up -d

# Build Lambda packages
cd infrastructure/sam-local && ./build.sh && cd ../..

# Run SAM local tests
pytest -m sam_local -v
```

**Location**: `tests/integration/sam_local/`

**Prerequisites**:
- Docker running
- LocalStack started
- Lambda packages built (see `infrastructure/sam-local/README.md`)

### 3. E2E Integration Tests (`-m integration`)

Tests against real AWS with deployed infrastructure.

```bash
# Requires deployed infrastructure
pytest -m integration -v
```

**Location**: `tests/integration/` (non-sam_local files)

**Runs in CI after CDK deploy.**

## Running Tests

### Daily Development

```bash
# Unit tests (fast feedback)
pytest -m unit -v

# Unit tests with coverage
pytest -m unit --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Pre-Commit / Pre-Deploy

```bash
# 1. Start LocalStack
docker-compose -f infrastructure/sam-local/docker-compose.yml up -d

# 2. Build Lambda packages
cd infrastructure/sam-local && ./build.sh && cd ../..

# 3. Run unit + SAM local tests
pytest -m "unit or sam_local" -v

# 4. Lint and type check
ruff check src/ tests/
mypy src/
```

### Full CI Simulation

```bash
# Everything except real AWS tests
pytest -m "not integration" --cov=src --cov-report=term-missing
```

## Test Markers

| Marker | Description | AWS Required |
|--------|-------------|--------------|
| `unit` | Unit tests with mocked dependencies | No |
| `sam_local` | SAM local invoke tests with LocalStack | No (Docker) |
| `integration` | Real AWS E2E tests | Yes |
| `slow` | Long-running tests | Varies |

## CI Workflow

The CI pipeline runs tests in parallel for fast feedback:

```
                         ┌─────────────────┐
                         │      lint       │
                         └────────┬────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐        ┌────────────────┐        ┌────────────────┐
│  Unit Tests   │        │ SAM Local Tests│        │  type-check    │
│ (coverage 79%)│        │ (packaging)    │        │  security      │
└───────┬───────┘        └───────┬────────┘        └───────┬────────┘
        │                        │                         │
        ▼                        │                         │
┌───────────────┐                │                         │
│   CDK Synth   │                │                         │
└───────┬───────┘                │                         │
        │                        │                         │
        └────────────────────────┴─────────────────────────┘
                                 │
                       ┌─────────▼─────────┐
                       │   all-checks      │◄── Gate for branch protection
                       └─────────┬─────────┘
                                 │
                  (on PR or [deploy] commit tag)
                                 │
                       ┌─────────▼─────────┐
                       │    CDK Deploy     │
                       └─────────┬─────────┘
                                 │
                       ┌─────────▼─────────┐
                       │ Integration Tests │
                       │  (real AWS E2E)   │
                       └─────────┬─────────┘
                                 │
                       ┌─────────▼─────────┐
                       │   CDK Destroy     │
                       │ (cleanup sandbox) │
                       └───────────────────┘
```

**Note:** CDK Synth runs after Unit Tests to validate CloudFormation templates.
All jobs must pass `all-checks` before deployment can proceed.

### Why SAM Tests Don't Have Coverage

SAM local tests invoke Lambda handlers via `sam local invoke`, which runs code in Docker containers. pytest-cov only measures code in the same Python process, so SAM tests can't contribute to source coverage.

**SAM tests validate that code *runs*. Unit tests validate code *coverage*.**

## Coverage Targets

- **Unit tests**: 79% (measured in CI)
- **Integration tests**: 60% (measured in CI after deploy)

## Key Files

- `tests/integration/conftest.py` - Shared fixtures (LocalStack, real AWS)
- `tests/integration/sam_local/conftest.py` - SAM local invoker fixtures
- `infrastructure/sam-local/` - SAM template, build script, docker-compose
- `pyproject.toml` - Pytest and coverage configuration

## Troubleshooting

### LocalStack not running

```bash
docker-compose -f infrastructure/sam-local/docker-compose.yml up -d
curl http://localhost:4566/_localstack/health
```

### SAM build not found

```bash
cd infrastructure/sam-local && ./build.sh
```

### Lambda can't reach LocalStack

The SAM template uses `host.docker.internal:4566` which works on Mac/Windows.
On Linux, you may need `--network host` flag.

## Adding Tests for New Features

When adding a new Lambda handler or feature, follow this checklist:

### 1. Unit Tests (Required)

Add unit tests in `tests/unit/` with mocked dependencies:

```python
@pytest.mark.unit
class TestMyNewHandler:
    def test_success_case(self, mock_dynamodb):
        # Test with mocked DynamoDB
        ...
```

### 2. SAM Local Tests (Required for Lambda handlers)

For new Lambda handlers, add SAM local tests:

**a) Add handler to SAM template** (`infrastructure/sam-local/template.yaml`):
```yaml
MyNewFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: .aws-sam/build/MyNewFunction
    Handler: src.my_module.handler
    Environment:
      Variables:
        MY_TABLE: MyTable
```

**b) Update build script** (`infrastructure/sam-local/build.sh`):
```bash
for func in ListAgentsFunction GetAgentFunction ... MyNewFunction; do
```

**c) Add event file** (`infrastructure/sam-local/events/my_event.json`):
```json
{
  "httpMethod": "GET",
  "path": "/my-resource",
  ...
}
```

**d) Add test** (`tests/integration/sam_local/test_my_handler.py`):
```python
@pytest.mark.sam_local
@pytest.mark.slow
class TestMyNewHandler:
    def test_with_event_file(self, sam_invoker):
        response = sam_invoker.invoke_with_event_file("MyNewFunction", "my_event.json")
        assert response["statusCode"] == 200
```

### 3. Integration Tests (For E2E validation)

Add integration tests that run against real AWS:

```python
@pytest.mark.integration
class TestMyFeatureE2E:
    def test_real_aws_behavior(self, api_url):
        # Test against deployed API
        ...
```

### New DynamoDB Tables

If your feature needs a new DynamoDB table:

1. Add to CDK stack (`infrastructure/cdk/`)
2. Add to LocalStack init script (`infrastructure/sam-local/init-localstack.sh`)
3. Add to CI workflow (`.github/workflows/ci.yml` - "Create DynamoDB tables" step)

---

**Last Updated**: 2026-01-17
