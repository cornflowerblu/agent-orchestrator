---
name: ralph-integration
description: Autonomous AWS integration testing loop - deploys CDK infrastructure, runs integration tests, fixes issues, and cleans up
---

# Ralph Integration - AWS Infrastructure Testing Loop

Autonomous loop for deploying CDK infrastructure, running integration tests, auto-fixing issues, and cleaning up resources.

## Usage

```bash
/ralph-integration
/ralph-integration --max-iterations=15
/ralph-integration --profile=sandbox
/ralph-integration --promise=INTEGRATION_TESTS_PASS
/ralph-integration --skip-destroy  # Keep infra up for debugging
```

## What This Does

**The Flow:**

1. **SAM Local Sanity Check** - Test Lambda packaging locally before CDK (fast gate)
2. **CDK Synth** - Validate CloudFormation templates
3. **CDK Deploy** - Deploy all stacks to AWS
4. **Integration Tests** - Run pytest -m integration
5. **Auto-Fix** - If failures, diagnose and fix automatically
6. **CDK Destroy** - Clean up all resources (guaranteed)

**Loop continues until:**

- ✅ All integration tests pass (success)
- ❌ Max iterations reached (failure)
- 🛑 User interrupts

## Parameters

- `--max-iterations=N` - Maximum deployment attempts (default: 10)
- `--promise=NAME` - Success promise to output (default: INTEGRATION_TESTS_PASS)
- `--skip-destroy` - Keep infrastructure deployed (for debugging)
- `--skip-sam-check` - Skip SAM local sanity check (not recommended)
- `--profile=PROFILE` - AWS CLI profile to use (e.g., sandbox, production)
- `--region=REGION` - AWS region (default: us-east-1)
- `--account-id=ID` - AWS account ID (auto-detected from AWS CLI)

## The Workflow

### Phase 1: Pre-Flight Checks

Before starting the loop:

1. **Check AWS Credentials**

   ```bash
   # Export AWS_PROFILE if --profile was provided
   export AWS_PROFILE=sandbox  # if --profile=sandbox
   aws sts get-caller-identity
   ```

   - Verify AWS credentials are configured
   - Confirm account ID matches expected
   - Check region is set
   - Note: If `--profile` is specified, export `AWS_PROFILE` before all AWS/CDK commands

2. **Check CDK Bootstrap**

   ```bash
   cdk bootstrap --show-template
   ```

   - Verify account is bootstrapped for CDK
   - If not, run: `cdk bootstrap aws://ACCOUNT/REGION`

3. **Check Python Dependencies**

   ```bash
   source .venv/bin/activate
   pip list | grep -E "aws-cdk|boto3|pytest"
   ```

   - Verify CDK and test dependencies installed
   - Install if missing

4. **Check Integration Test Markers**

   ```bash
   pytest --markers | grep integration
   ```

   - Verify integration tests exist
   - Count total integration tests to run

### Phase 1.5: SAM Local Sanity Check (Pre-Deploy Gate)

**Purpose:** Catch Lambda packaging/configuration issues in ~60 seconds before committing to expensive CDK deploys.

**What it catches that unit tests don't:**

- Handler entry point typos in template.yaml
- Missing dependencies in Lambda packages
- Environment variable misconfiguration
- Import errors in packaged artifacts

1. **Start LocalStack**

   ```bash
   docker compose -f infrastructure/sam-local/docker-compose.yml up -d
   # Wait for LocalStack to be healthy
   ```

2. **Build SAM Application**

   ```bash
   cd infrastructure/sam-local
   ./build.sh
   ```

3. **Run SAM Local Tests**

   ```bash
   cd ../..  # Back to project root
   pytest tests/integration/sam_local -m integration_sam -v --tb=short
   ```

4. **Gate Decision**
   - ✅ **SAM tests pass** → Proceed to Phase 2 (CDK Deploy)
   - ❌ **SAM tests fail** → **EXIT EARLY**
     - Don't waste time on CDK deploy
     - Fix Lambda issues first
     - Re-run `/ralph-integration` after fixing

**Common Issues & Auto-Fixes:**

| Error                       | Auto-Fix                               |
| --------------------------- | -------------------------------------- |
| `LocalStack not running`    | `docker compose up -d`                 |
| `sam build failed`          | Check handler paths in template.yaml   |
| `ModuleNotFoundError`       | Fix requirements.txt or pyproject.toml |
| `Handler not found`         | Fix handler entry point string         |
| `Connection refused (4566)` | Wait for LocalStack, retry             |

**Why This Gate Matters:**

- SAM local test: ~60 seconds
- CDK deploy cycle: ~5-10 minutes
- If Lambdas are broken, CDK deploy will fail anyway
- Fail fast, fix fast

### Phase 2: Deployment Loop

**Iteration N (max: --max-iterations):**

#### Step 1: CDK Synth

```bash
cd infrastructure/cdk
export AWS_PROFILE=sandbox  # if --profile was provided
source ../../.venv/bin/activate
cdk synth --all
```

**Common Issues & Auto-Fixes:**

| Error                          | Auto-Fix                             |
| ------------------------------ | ------------------------------------ |
| `ModuleNotFoundError: aws_cdk` | `pip install aws-cdk-lib constructs` |
| `Resolution error`             | Check pyproject.toml dependencies    |
| `Invalid identifier`           | Fix Python syntax in stack files     |
| `Property validation failed`   | Fix CDK construct parameters         |

#### Step 2: CDK Deploy

```bash
export AWS_PROFILE=sandbox  # if --profile was provided
source ../../.venv/bin/activate
cdk deploy --all --require-approval never --outputs-file outputs.json
```

**Common Issues & Auto-Fixes:**

| Error                      | Auto-Fix                                   |
| -------------------------- | ------------------------------------------ |
| `Resource limit exceeded`  | Request limit increase or use different AZ |
| `Stack already exists`     | Check if from previous run, destroy first  |
| `Insufficient permissions` | Check IAM role has required permissions    |
| `DependencyViolation`      | Adjust depends_on in CDK code              |
| `CREATE_FAILED`            | Read CloudFormation events, fix root cause |
| `ROLLBACK_COMPLETE`        | Destroy stack, fix issue, retry            |

**Timeout Strategy:**

- Wait up to 20 minutes for stack creation
- Poll every 30 seconds for status
- If stuck in CREATE_IN_PROGRESS > 20 min, investigate

#### Step 3: Run Integration Tests

```bash
cd ../..  # Back to project root
export AWS_PROFILE=sandbox  # if --profile was provided
export AWS_REGION=us-east-1
source .venv/bin/activate
# Integration tests use 60% coverage threshold (vs 80% for unit tests)
# Industry standard: integration tests 70-80%, unit tests 80-95%
pytest -m integration -v --tb=short --maxfail=1 --cov=src --cov-report=term-missing --cov-fail-under=60
```

**Test Environment Setup:**

- Load stack outputs from `infrastructure/cdk/outputs.json`
- Set environment variables for tests:
  - `TABLE_NAME_METADATA` from outputs
  - `TABLE_NAME_STATUS` from outputs
  - `API_URL` from outputs
  - `AWS_REGION` from config

**Common Issues & Auto-Fixes:**

| Error                 | Auto-Fix                                                |
| --------------------- | ------------------------------------------------------- |
| `No tests collected`  | Check @pytest.mark.integration decorators               |
| `Fixture not found`   | Add conftest.py with fixtures                           |
| `Connection timeout`  | Check VPC/security group settings                       |
| `AccessDenied`        | Update IAM permissions in test role                     |
| `ResourceNotFound`    | Verify stack outputs are correct                        |
| `ThrottlingException` | Add retry logic with backoff                            |
| `Coverage < 60%`      | Add more integration tests for uncovered critical paths |

#### Step 4: Analyze Failures

If tests fail:

1. **Capture Test Output**
   - Save full pytest output
   - Extract stack traces
   - Identify failure patterns

2. **Check CloudWatch Logs**

   ```bash
   aws logs tail /aws/lambda/FUNCTION_NAME --follow --since 10m
   ```

   - Look for Lambda errors
   - Check API Gateway logs
   - Review DynamoDB errors

3. **Categorize Failure Type:**
   - **Infrastructure**: CDK config issue → Fix stack code
   - **Permissions**: IAM issue → Update policies
   - **Logic**: Code bug → Fix source code
   - **Timing**: Race condition → Add retries/waits
   - **Data**: Test data issue → Fix test fixtures
   - **Coverage**: Coverage < 60% → Add more integration tests for uncovered paths

4. **Apply Fix**
   - Edit relevant files
   - Commit changes locally (using /commit to validate unit tests still pass)
   - Continue to next iteration

**Note on Coverage Failures:**

- Coverage failures are treated like test failures - we destroy and iterate
- This ensures clean state for next deployment with updated tests
- Use `--skip-destroy` only if you need to debug infrastructure while adding tests

### Phase 3: Cleanup (Always Runs)

**Guaranteed cleanup even on failure:**

```bash
cd infrastructure/cdk
export AWS_PROFILE=sandbox  # if --profile was provided
source ../../.venv/bin/activate
cdk destroy --all --force
```

**Cleanup Verification:**

- Wait for DELETE_COMPLETE status
- Check no stacks remain: `aws cloudformation list-stacks`
- Verify no orphaned resources (DynamoDB tables, S3 buckets)

**If destroy fails:**

- Manually delete stuck resources
- Force delete via AWS Console if needed
- Warn user about remaining resources

**Skip cleanup with:** `--skip-destroy`

- Useful for debugging failures
- User must manually destroy later
- Warn about ongoing AWS charges

### Phase 4: Success/Failure Reporting

**On Success (all tests pass):**

```
✅ Integration Tests PASSED (iteration N)

Summary:
- CDK Stacks: 3 deployed, 3 destroyed
- Tests: 15/15 passed
- Duration: X minutes
- Fixes applied: N

<promise>INTEGRATION_TESTS_PASS</promise>
```

**On Failure (max iterations reached):**

```
❌ Integration Tests FAILED (max iterations: 10)

Last error:
[Error details]

Attempted fixes:
1. [Fix 1]
2. [Fix 2]

Recommendations:
- Manual intervention required
- Check CloudWatch logs
- Review stack events

Infrastructure state: DESTROYED
```

## Auto-Fix Strategies

### 1. IAM Permission Errors

**Detection:** `AccessDenied`, `UnauthorizedOperation`

**Fix Strategy:**

1. Identify missing permission from error message
2. Update IAM policy in CDK stack
3. Redeploy with new permissions

### 2. Resource Quota/Limits

**Detection:** `LimitExceeded`, `Throttling`

**Fix Strategy:**

1. Check current quotas: `aws service-quotas list-service-quotas`
2. If soft limit, request increase
3. Otherwise, reduce resource usage or change region

### 3. Network/VPC Issues

**Detection:** `VPCResourceNotAvailable`, `SubnetNotFound`

**Fix Strategy:**

1. Verify VPC exists in region
2. Check subnet availability zones
3. Update CDK to use available AZs

### 4. Dependency/Timing Issues

**Detection:** `DependencyViolation`, `ResourceNotReady`

**Fix Strategy:**

1. Add explicit `depends_on` in CDK
2. Increase timeouts for slow resources
3. Add retry logic in tests

### 5. Data/State Issues

**Detection:** Tests fail due to incorrect data

**Fix Strategy:**

1. Reset DynamoDB tables (delete all items)
2. Update test fixtures with correct data
3. Add proper test isolation

## Best Practices

### During Loop

1. **Log Everything**
   - Capture all command output
   - Save CloudFormation events
   - Store test results per iteration

2. **Incremental Fixes**
   - Fix one issue at a time
   - Verify fix before moving to next
   - Don't make multiple changes simultaneously

3. **Resource Tagging**
   - Tag all resources with `TestRun: ralph-integration-{timestamp}`
   - Makes cleanup easier if destroy fails

### After Success

1. **Review Changes**
   - Check what was fixed during iterations
   - Commit valuable fixes
   - Discard temporary workarounds

2. **Update Tests**
   - Add new test cases for found issues
   - Improve test reliability
   - Document integration test setup

### After Failure

1. **Preserve State**
   - Keep last error logs
   - Save CloudFormation events
   - Document failure pattern

2. **Manual Investigation**
   - Review AWS Console
   - Check CloudWatch Logs Insights
   - Examine resource states

## Safety Guardrails

1. **Cost Protection**
   - Warn if iteration > 5 (AWS charges accumulating)
   - Estimate cost per iteration
   - Require confirmation for expensive resources

2. **Cleanup Guarantee**
   - ALWAYS run destroy (unless --skip-destroy)
   - Verify all resources deleted
   - Alert on orphaned resources

3. **Region Locking**
   - Only deploy to specified region
   - Prevent accidental cross-region resources
   - Validate region before deploy

4. **Iteration Limits**
   - Hard stop at max iterations
   - No infinite loops
   - Clear failure reporting

## Example Session

```bash
$ /ralph-integration --max-iterations=5

Ralph Integration Loop Starting...

Pre-Flight Checks:
✓ AWS credentials configured (account: 712672311059)
✓ CDK bootstrap verified
✓ Python dependencies installed
✓ Found 15 integration tests

SAM Local Sanity Check:
✓ LocalStack running (localhost:4566)
✓ sam build completed (3 functions)
✓ SAM local tests: 8/8 passed (47s)
→ Proceeding to CDK deployment

Iteration 1:
- CDK Synth: ✓ (3 stacks)
- CDK Deploy: ✗ (MetadataStack failed - insufficient permissions)
- Auto-Fix: Added dynamodb:* to IAM policy

Iteration 2:
- CDK Synth: ✓
- CDK Deploy: ✓ (3 stacks, 5 minutes)
- Integration Tests: ✗ (3/15 failed - connection timeout)
- Auto-Fix: Updated security group ingress rules

Iteration 3:
- CDK Synth: ✓
- CDK Deploy: ✓ (updated stack, 2 minutes)
- Integration Tests: ✓ (15/15 passed!)
- CDK Destroy: ✓ (cleanup complete)

✅ Success in 3 iterations!

<promise>INTEGRATION_TESTS_PASS</promise>
```

**Example: Early Exit on SAM Failure**

```bash
$ /ralph-integration --max-iterations=5

Ralph Integration Loop Starting...

Pre-Flight Checks:
✓ AWS credentials configured (account: 712672311059)
✓ CDK bootstrap verified
✓ Python dependencies installed
✓ Found 15 integration tests

SAM Local Sanity Check:
✓ LocalStack running (localhost:4566)
✓ sam build completed (3 functions)
✗ SAM local tests: 2/8 failed (23s)
  - test_list_agents_handler: ModuleNotFoundError: No module named 'pydantic'
  - test_update_metadata_handler: Handler 'src.registry.handlers.update_metadata' not found

❌ SAM Local Gate FAILED - Skipping CDK deployment

Fix the Lambda packaging issues and re-run /ralph-integration
Hint: Check requirements.txt and handler paths in template.yaml
```

## Constitutional Compliance

This skill implements:

- ✅ **Principle III (Verification-First)**: Tests must pass before claiming success
- ✅ **Principle VII (Autonomous Learning)**: Auto-fixes issues without manual intervention
- ✅ **Principle II (Infrastructure as Code)**: All infra defined in CDK, no manual clicks
- ✅ **Fail Fast**: SAM local gate catches Lambda issues before expensive CDK deploys

## Advanced Usage

### Custom Test Subsets

```bash
/ralph-integration --tests="tests/integration/test_registry.py::test_api_endpoints"
```

### Multi-Region Testing

```bash
/ralph-integration --region=us-west-2
```

### Different AWS Profile

```bash
/ralph-integration --profile=sandbox
/ralph-integration --profile=production --region=us-west-2
```

### Preserve Infrastructure

```bash
/ralph-integration --skip-destroy
# Infrastructure stays up for manual testing
# Don't forget to destroy manually later!
```

### Integration with CI/CD

While this skill is designed for local development, the same pattern can be automated in CI:

```yaml
# .github/workflows/integration-test.yml
- name: Run Integration Tests
  run: |
    # Same workflow but in CI
    cdk deploy --all
    pytest -m integration
    cdk destroy --all --force
```

---

**Remember:** This is an autonomous loop. Once started, it will keep trying until success or max iterations. Use wisely! 🔄
