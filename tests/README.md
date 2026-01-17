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

## Coverage Targets

- **Unit tests**: 80%
- **Integration tests**: 60%

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

---

**Last Updated**: 2026-01-17
