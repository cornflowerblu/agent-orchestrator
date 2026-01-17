# Testing Workflow

This document describes the three-tier testing strategy for the agent-orchestrator project, how to run tests, and best practices for adding new tests.

## Table of Contents

- [Overview](#overview)
- [Test Tiers](#test-tiers)
- [Running Tests](#running-tests)
- [Coverage Targets](#coverage-targets)
- [Local vs AWS Testing](#local-vs-aws-testing)
- [Adding New Tests](#adding-new-tests)
- [Test Fixtures](#test-fixtures)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

## Overview

The project uses a **three-tier testing strategy** designed to provide fast feedback during development while ensuring production readiness through comprehensive integration testing.

```
┌─────────────────────┬──────────────┬──────────────┬────────────────┐
│ Tier                │ Speed        │ Coverage     │ AWS Required   │
├─────────────────────┼──────────────┼──────────────┼────────────────┤
│ Unit Tests          │ Fastest      │ 80% target   │ No (mocked)    │
│ Local Integration   │ Fast (3.8s)  │ 60% target   │ No (moto)      │
│ E2E Integration     │ Slow         │ 60% target   │ Yes (real AWS) │
└─────────────────────┴──────────────┴──────────────┴────────────────┘
```

### Why Three Tiers?

1. **Unit Tests** - Validate individual components in isolation with comprehensive mocking
2. **Local Integration** - Test component interactions using moto (AWS service mocks) for rapid iteration
3. **E2E Integration** - Verify real AWS behavior against deployed infrastructure before production

This approach provides:
- **Fast feedback loops** during development (unit + local integration)
- **Confidence in AWS integration** before deployment (E2E)
- **Cost efficiency** by minimizing real AWS usage during development

## Test Tiers

### 1. Unit Tests (`-m unit`)

**Purpose**: Test individual functions, classes, and methods in complete isolation.

**Characteristics**:
- Fully mocked dependencies (DynamoDB, Bedrock, external services)
- No network calls
- Fast execution (milliseconds per test)
- 80% coverage target

**Location**: `/Users/rurich/Development/agent-orchestrator/tests/unit/`

**Test Files** (12 files):
- `test_validation.py` - Input/output validation logic
- `test_gateway_tools.py` - Gateway tool implementations
- `test_base_agent.py` - Base agent functionality
- `test_metadata_models.py` - Metadata model validation
- `test_consultation_rules.py` - Consultation rule logic
- `test_discovery.py` - Agent discovery mechanisms
- `test_metadata_storage.py` - Storage layer (mocked)
- `test_exceptions.py` - Exception handling
- `test_consultation_enforcement.py` - Consultation enforcement logic
- `test_query.py` - Query operations
- `test_status_storage.py` - Status storage layer
- `test_handlers.py` - Lambda handler logic

### 2. Local Integration Tests (`-m integration_local`)

**Purpose**: Test component interactions using moto-based AWS service mocks.

**Characteristics**:
- Uses moto for DynamoDB, S3, and other AWS services
- Tests real component interactions without AWS deployment
- Fast execution (~3.81 seconds for 69 tests)
- 60% coverage target
- Perfect for rapid development iteration

**Location**: `/Users/rurich/Development/agent-orchestrator/tests/integration/`

**Test Files** (5 files ending in `_local.py`):
- `test_metadata_storage_local.py` - Metadata CRUD operations
- `test_status_storage_local.py` - Status tracking operations
- `test_registry_query_local.py` - Registry query functionality
- `test_consultation_enforcement_local.py` - Consultation flow testing
- `test_metadata_validation_local.py` - Schema validation integration

**Current Stats**:
- 69 tests passing
- 3.81 seconds total runtime
- 55.77% combined coverage (unit + local integration)

### 3. E2E Integration Tests (`-m integration`)

**Purpose**: Validate behavior against real AWS services with deployed infrastructure.

**Characteristics**:
- Requires AWS credentials and deployed DynamoDB tables
- Tests actual AWS API behavior
- Slower execution (network latency, real operations)
- 60% coverage target
- Runs in CI/CD after CDK deployment

**Location**: `/Users/rurich/Development/agent-orchestrator/tests/integration/`

**Test Files** (2 files ending in `_e2e.py`):
- `test_metadata_storage_e2e.py` - Real DynamoDB metadata operations
- `test_status_storage_e2e.py` - Real DynamoDB status operations

**AWS Requirements**:
- Deployed `AgentMetadata` DynamoDB table
- Deployed `AgentStatus` DynamoDB table
- Valid AWS credentials with appropriate permissions
- Environment variables: `AWS_REGION`, `AGENT_METADATA_TABLE`, `AGENT_STATUS_TABLE`

## Running Tests

### Prerequisites

1. **Activate virtual environment**:
   ```bash
   cd /Users/rurich/Development/agent-orchestrator
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

### Basic Commands

```bash
# Run all unit tests
pytest -m unit -v

# Run all local integration tests
pytest -m integration_local -v

# Run all E2E integration tests (requires AWS deployment)
pytest -m integration -v

# Run all tests except E2E integration
pytest -m "not integration" -v
```

### With Coverage

```bash
# Unit tests with 80% coverage threshold
pytest -m unit --cov=src --cov-report=term-missing --cov-fail-under=80

# Local integration tests with 60% coverage threshold
pytest -m integration_local --cov=src --cov-report=term-missing --cov-fail-under=60

# E2E integration tests with 60% coverage threshold
pytest -m integration --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=60

# Combined unit + local integration (current development workflow)
pytest -m "unit or integration_local" --cov=src --cov-report=term-missing
```

### Specific Test Files

```bash
# Run specific test file
pytest tests/integration/test_metadata_storage_local.py -v

# Run specific test class
pytest tests/unit/test_metadata_storage.py::TestMetadataStorage -v

# Run specific test method
pytest tests/integration/test_metadata_storage_local.py::TestMetadataStorageLocal::test_put_and_get_metadata -v

# Run with verbose output and show print statements
pytest tests/integration/test_metadata_storage_local.py -v -s
```

### Advanced Options

```bash
# Show slowest 10 tests
pytest --durations=10

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# View at htmlcov/index.html
```

## Coverage Targets

### Unit Tests: 80%

**Rationale**: Unit tests should cover the majority of code logic since they're fast and easy to maintain. Higher coverage ensures edge cases and error paths are tested.

**Configuration**: Set in `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 80
```

**Enforcement**: CI/CD fails if unit test coverage drops below 80%.

### Local Integration Tests: 60%

**Rationale**: Integration tests focus on component interactions rather than exhaustive code paths. Lower threshold allows focus on critical integration points while avoiding test duplication.

**Enforcement**: Manual threshold in test commands:
```bash
pytest -m integration_local --cov-fail-under=60
```

### E2E Integration Tests: 60%

**Rationale**: E2E tests validate real AWS behavior for critical paths. Lower coverage is acceptable since:
- E2E tests are slower and more expensive
- Many code paths are already covered by unit and local integration tests
- Focus is on production-critical scenarios

**Enforcement**: CI/CD runs with `--cov-fail-under=60` after deployment.

### Current Combined Coverage

As of latest run:
- **Unit + Local Integration**: 55.77%
- **Goal**: Increase to 70%+ combined coverage

## Local vs AWS Testing

### When to Use Local Integration Tests

✅ **Use local integration tests for**:
- Rapid development and iteration
- Testing component interactions (storage + models + validation)
- Schema validation and data transformation
- Error handling and edge cases
- Pre-commit verification
- Most development scenarios

**Example**: Testing metadata storage CRUD operations
```python
# tests/integration/test_metadata_storage_local.py
pytestmark = pytest.mark.integration_local

def test_put_and_get_metadata(metadata_storage, sample_metadata):
    metadata_storage.put_metadata(sample_metadata)
    retrieved = metadata_storage.get_metadata(sample_metadata.agent_name)
    assert retrieved.agent_name == sample_metadata.agent_name
```

### When to Use E2E Integration Tests

✅ **Use E2E integration tests for**:
- Validating AWS-specific behavior (DynamoDB Streams, GSI queries, etc.)
- Testing IAM permissions and resource policies
- Verifying CloudFormation/CDK infrastructure
- Pre-deployment validation
- Production readiness checks

**Example**: Testing real DynamoDB operations
```python
# tests/integration/test_metadata_storage_e2e.py
pytestmark = pytest.mark.integration

def test_put_and_get_metadata(metadata_storage, sample_metadata):
    # Same test, but runs against real AWS DynamoDB
    metadata_storage.put_metadata(sample_metadata)
    retrieved = metadata_storage.get_metadata(sample_metadata.agent_name)
    assert retrieved.agent_name == sample_metadata.agent_name
```

### Workflow Recommendation

1. **Development Phase**: Write and run local integration tests (`-m integration_local`)
2. **Pre-commit**: Run unit + local integration tests
3. **Pre-deployment**: Let CI/CD run E2E tests after infrastructure deployment
4. **Production Issues**: Add both local and E2E tests to prevent regressions

## Adding New Tests

### 1. Unit Test Template

```python
# tests/unit/test_my_feature.py
import pytest
from unittest.mock import Mock, patch

pytestmark = pytest.mark.unit

class TestMyFeature:
    """Unit tests for my feature."""

    def test_basic_functionality(self):
        """Test the happy path."""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = my_function(input_data)

        # Assert
        assert result["status"] == "success"

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError):
            my_function(None)

    @patch("src.my_module.external_dependency")
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependencies."""
        mock_dependency.return_value = "mocked"
        result = my_function_with_dependency()
        assert result == "mocked"
```

### 2. Local Integration Test Template

```python
# tests/integration/test_my_feature_local.py
import pytest

pytestmark = pytest.mark.integration_local

@pytest.fixture
def my_storage(dynamodb_local):
    """Create storage instance with mocked DynamoDB."""
    from src.my_module.storage import MyStorage
    return MyStorage(table_name="MyTable", region="us-east-1")

@pytest.fixture
def sample_data():
    """Sample test data."""
    return {
        "id": "test-id",
        "name": "test-name",
        "status": "active"
    }

class TestMyFeatureLocal:
    """Local integration tests using moto."""

    def test_create_and_retrieve(self, my_storage, sample_data):
        """Test creating and retrieving data."""
        # Create
        my_storage.create(sample_data)

        # Retrieve
        retrieved = my_storage.get(sample_data["id"])

        # Verify
        assert retrieved["name"] == sample_data["name"]
        assert retrieved["status"] == sample_data["status"]
```

### 3. E2E Integration Test Template

```python
# tests/integration/test_my_feature_e2e.py
import os
import pytest

pytestmark = pytest.mark.integration

@pytest.fixture
def my_storage():
    """Create storage instance with real DynamoDB."""
    from src.my_module.storage import MyStorage
    return MyStorage(
        table_name=os.getenv("MY_TABLE_NAME", "MyTable"),
        region=os.getenv("AWS_REGION", "us-east-1")
    )

class TestMyFeatureE2E:
    """E2E tests with real AWS services."""

    def test_real_aws_operation(self, my_storage):
        """Test against real DynamoDB."""
        # Test real AWS behavior
        result = my_storage.complex_operation()
        assert result is not None
```

### Key Patterns

#### ✅ DO: Use pytestmark for test marking
```python
pytestmark = pytest.mark.integration_local  # Marks all tests in file
```

#### ✅ DO: Use shared fixtures from conftest.py
```python
def test_my_test(dynamodb_local, metadata_storage):
    # Fixtures are automatically available
    pass
```

#### ✅ DO: Follow schema patterns
```python
# OutputSchema MUST have 'guaranteed' field
OutputSchema(
    semantic_type=SemanticType.ARTIFACT,
    name="output",
    description="Test output",
    guaranteed=True  # Required!
)

# Use correct enum values
semantic_type=SemanticType.DOCUMENT  # Not "document"
semantic_type=SemanticType.ARTIFACT  # Not "artifact"
```

#### ❌ DON'T: Mark individual tests (use pytestmark instead)
```python
# Bad
@pytest.mark.integration_local
def test_something():
    pass

# Good
pytestmark = pytest.mark.integration_local
def test_something():
    pass
```

#### ❌ DON'T: Create duplicate fixtures (use conftest.py)
```python
# Bad - duplicating fixture in test file
@pytest.fixture
def dynamodb_local():
    # ... duplicate setup

# Good - use from conftest.py
def test_my_test(dynamodb_local):
    # Fixture automatically available
    pass
```

## Test Fixtures

### Global Fixtures (tests/integration/conftest.py)

#### `aws_credentials_moto`
Sets up fake AWS credentials for moto mocking.

```python
@pytest.fixture
def aws_credentials_moto():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    # ... more setup
```

**Usage**: Automatically used by `dynamodb_local` fixture.

#### `dynamodb_local`
Creates fully configured mocked DynamoDB resource with both tables.

```python
@pytest.fixture
def dynamodb_local(aws_credentials_moto) -> Iterator[boto3.resource]:
    """Create mocked DynamoDB resource for local testing."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Creates AgentMetadata table with GSI
        # Creates AgentStatus table
        yield dynamodb
```

**Tables Created**:
- `AgentMetadata` - With `SkillIndex` GSI and DynamoDB Streams
- `AgentStatus` - Simple key-value store

**Usage**:
```python
def test_my_test(dynamodb_local):
    # Tables are already created and ready to use
    storage = MetadataStorage(table_name="AgentMetadata")
    storage.put_metadata(metadata)
```

#### `dynamodb_real`
Creates real DynamoDB resource for E2E tests.

```python
@pytest.fixture
def dynamodb_real() -> boto3.resource:
    """Create real DynamoDB resource for AWS integration tests."""
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
```

**Usage**:
```python
@pytest.mark.integration
def test_real_aws(dynamodb_real):
    # Uses real AWS credentials and deployed tables
    table = dynamodb_real.Table("AgentMetadata")
```

### Custom Fixtures (Per Test File)

Most test files define their own fixtures for test data and storage instances:

```python
@pytest.fixture
def metadata_storage(dynamodb_local):
    """Create metadata storage with mocked DynamoDB."""
    return MetadataStorage(table_name="AgentMetadata", region="us-east-1")

@pytest.fixture
def sample_metadata():
    """Sample agent metadata for testing."""
    return CustomAgentMetadata(
        agent_name="test-agent",
        version="1.0.0",
        input_schemas=[...],
        output_schemas=[...]
    )
```

### Fixture Scope

- **Function scope (default)**: Fresh instance for each test
  ```python
  @pytest.fixture  # New instance per test
  def my_fixture():
      return MyClass()
  ```

- **Class scope**: Shared across test class
  ```python
  @pytest.fixture(scope="class")
  def my_fixture():
      return MyClass()
  ```

- **Module scope**: Shared across entire module
  ```python
  @pytest.fixture(scope="module")
  def my_fixture():
      return MyClass()
  ```

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError: No module named 'src'

**Problem**: Python can't find the `src` package.

**Solution**: Install package in editable mode:
```bash
pip install -e .
```

#### 2. botocore.exceptions.NoCredentialsError

**Problem**: AWS credentials not configured for E2E tests.

**Solution**:
```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

#### 3. ResourceNotFoundException: Requested resource not found (DynamoDB)

**Problem**: E2E tests can't find deployed DynamoDB tables.

**Solution**:
```bash
# Verify tables exist
aws dynamodb list-tables --region us-east-1

# Set environment variables
export AGENT_METADATA_TABLE=AgentMetadata
export AGENT_STATUS_TABLE=AgentStatus

# Or deploy infrastructure
cd infrastructure/cdk
cdk deploy --all
```

#### 4. Tests pass locally but fail in CI

**Problem**: Different environments or missing dependencies.

**Common causes**:
- Missing environment variables in CI
- Different Python versions
- Timing issues in CI environment

**Solution**:
```yaml
# .github/workflows/ci.yml
env:
  AGENT_METADATA_TABLE: AgentMetadata
  AGENT_STATUS_TABLE: AgentStatus
  AWS_REGION: us-east-1
```

#### 5. ValidationError: OutputSchema missing 'guaranteed' field

**Problem**: Pydantic validation failing on OutputSchema.

**Solution**: Always include `guaranteed` field:
```python
# Bad
OutputSchema(
    semantic_type=SemanticType.ARTIFACT,
    name="output",
    description="Test output"
)

# Good
OutputSchema(
    semantic_type=SemanticType.ARTIFACT,
    name="output",
    description="Test output",
    guaranteed=True  # Required!
)
```

#### 6. Coverage below threshold

**Problem**: Test coverage below 80% (unit) or 60% (integration).

**Solution**:
```bash
# Find uncovered lines
pytest --cov=src --cov-report=term-missing

# Focus on uncovered modules
pytest tests/unit/test_my_module.py --cov=src.my_module --cov-report=term-missing

# Generate HTML report for detailed analysis
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

#### 7. Moto not mocking AWS calls

**Problem**: Tests are hitting real AWS instead of moto mocks.

**Solution**: Ensure proper mock context:
```python
# Bad - mock context not maintained
@pytest.fixture
def my_fixture():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
    return dynamodb  # Context exited!

# Good - mock context maintained
@pytest.fixture
def my_fixture():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        yield dynamodb  # Context stays active
```

### Debug Tips

```bash
# Show print statements and logging
pytest -v -s

# Show local variables on failure
pytest --showlocals

# Drop into debugger on failure
pytest --pdb

# Increase verbosity
pytest -vv

# Show test setup/teardown
pytest --setup-show
```

## CI/CD Integration

### GitHub Actions Workflow

The project uses a multi-stage CI/CD pipeline defined in `.github/workflows/ci.yml`:

```
┌─────────┐   ┌──────┐   ┌────────────┐   ┌─────────┐
│  Lint   │──▶│ Test │──▶│ Type Check │──▶│Security │
└─────────┘   └──────┘   └────────────┘   └─────────┘
                  │
                  ▼
           ┌──────────┐   ┌────────────┐   ┌────────────────┐   ┌─────────────┐
           │CDK Synth │──▶│ CDK Deploy │──▶│Integration Test│──▶│ CDK Destroy │
           └──────────┘   └────────────┘   └────────────────┘   └─────────────┘
```

### Pipeline Stages

#### 1. Lint
```yaml
- name: Run Ruff linter
  run: ruff check src/ tests/

- name: Run Ruff formatter check
  run: ruff format --check src/ tests/
```

#### 2. Test (Unit + Local Integration)
```yaml
- name: Run unit tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-report=term-missing -m "not integration"
```

**Runs**: All unit tests and local integration tests (excluding E2E)

**Coverage**: Uploads to Codecov for tracking

#### 3. Type Check
```yaml
- name: Run mypy
  run: mypy src/ --ignore-missing-imports
```

#### 4. Security Scan
```yaml
- name: Run Bandit security linter
  run: bandit -r src/ -ll -ii

- name: Check dependencies for vulnerabilities
  run: pip-audit
```

#### 5. CDK Synth
Validates CloudFormation templates can be synthesized.

#### 6. CDK Deploy
Deploys DynamoDB tables and infrastructure to AWS.

**Uses**: OIDC authentication (no static credentials needed)

#### 7. Integration Test (E2E)
```yaml
- name: Run integration tests
  run: |
    pytest -v -m integration --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=60
  env:
    AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
    AWS_REGION: us-east-1
```

**Runs**: Only E2E integration tests against deployed infrastructure

**Coverage Threshold**: 60%

#### 8. CDK Destroy
Cleans up deployed resources after tests complete.

**Runs**: Always, even if tests fail (ensures no resource leaks)

### Required Secrets and Variables

Configure in GitHub repository settings:

**Secrets**:
- `AWS_ROLE_ARN` - IAM role for OIDC authentication
- `CODECOV_TOKEN` - Token for coverage uploads

**Variables**:
- `AWS_ACCOUNT_ID` - Your AWS account ID

### Local CI Simulation

Run the same checks locally before pushing:

```bash
# 1. Lint
ruff check src/ tests/
ruff format --check src/ tests/

# 2. Unit + Local Integration Tests
pytest -m "not integration" --cov=src --cov-report=term-missing

# 3. Type Check
mypy src/ --ignore-missing-imports

# 4. Security Scan
bandit -r src/ -ll -ii
pip-audit

# 5. CDK Synth (optional)
cd infrastructure/cdk
cdk synth --all
```

### Coverage Tracking

**Codecov Integration**:
- Unit test coverage uploaded with flag: `unittests`
- Integration test coverage uploaded with flag: `integration`
- View reports at: `https://codecov.io/gh/YOUR_ORG/agent-orchestrator`

**Artifacts**:
- Coverage XML files retained for 30 days
- Accessible from GitHub Actions "Summary" tab

---

## Quick Reference

### Essential Commands
```bash
# Daily development workflow
pytest -m "unit or integration_local" --cov=src --cov-report=term-missing

# Pre-commit checks
pytest -m "not integration" --cov=src --cov-report=term-missing --cov-fail-under=80
ruff check src/ tests/

# E2E validation (after deployment)
pytest -m integration --cov=src --cov-report=term-missing --cov-fail-under=60
```

### Test Markers
- `unit` - Fast, fully mocked unit tests
- `integration_local` - Moto-based local integration tests
- `integration` - Real AWS E2E integration tests
- `contract` - Contract/schema validation tests
- `slow` - Long-running tests

### Coverage Thresholds
- **Unit tests**: 80% (enforced in CI)
- **Local integration**: 60% (manual)
- **E2E integration**: 60% (enforced in CI)

### Key Files
- `/Users/rurich/Development/agent-orchestrator/tests/integration/conftest.py` - Shared fixtures
- `/Users/rurich/Development/agent-orchestrator/pyproject.toml` - Pytest and coverage configuration
- `/Users/rurich/Development/agent-orchestrator/.github/workflows/ci.yml` - CI/CD pipeline

---

**Last Updated**: 2026-01-17
**Test Count**: 24 test files (12 unit, 5 local integration, 2 E2E, 5 other)
**Current Coverage**: 55.77% (unit + local integration combined)
