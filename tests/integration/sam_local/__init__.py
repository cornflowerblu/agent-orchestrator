"""SAM Local integration tests.

Pre-deploy sanity tests that invoke actual Lambda functions via SAM local,
hitting LocalStack for DynamoDB and CloudWatch.

These tests catch packaging, handler configuration, and integration issues
that mocked tests miss.
"""
