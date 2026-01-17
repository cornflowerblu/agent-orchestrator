#!/bin/bash
# Manual build script for SAM local testing
# Run this instead of 'sam build'

set -e

PROJECT_ROOT="$(cd ../.. && pwd)"
BUILD_DIR=".aws-sam/build"

# Use venv pip if available, otherwise system pip
if [ -f "$PROJECT_ROOT/.venv/bin/pip" ]; then
    PIP="$PROJECT_ROOT/.venv/bin/pip"
else
    PIP="pip"
fi

echo "Building Lambda packages..."
echo "Project root: $PROJECT_ROOT"
echo "Using pip: $PIP"

# Clean previous build
rm -rf "$BUILD_DIR"

# Build each API function
for func in ListAgentsFunction GetAgentFunction UpdateMetadataFunction \
            GetConsultationFunction CheckCompatibilityFunction FindCompatibleFunction \
            GetStatusFunction UpdateStatusFunction; do
    echo "Building $func..."
    mkdir -p "$BUILD_DIR/$func"

    # Install dependencies for Linux x86_64 Python 3.11 (Lambda runtime)
    $PIP install pydantic boto3 \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.11 \
        --only-binary=:all: \
        --target "$BUILD_DIR/$func/" \
        --quiet

    # Copy source code
    cp -r "$PROJECT_ROOT/src" "$BUILD_DIR/$func/"
done

# Copy standalone handlers (no deps needed - they only use boto3 which is in Lambda runtime)
echo "Building ToolRegistryFunction..."
mkdir -p "$BUILD_DIR/ToolRegistryFunction"
cp ../cdk/lambda/tool_registry.py "$BUILD_DIR/ToolRegistryFunction/"

echo "Building PolicyEnforcerFunction..."
mkdir -p "$BUILD_DIR/PolicyEnforcerFunction"
cp ../cdk/lambda/policy_enforcer.py "$BUILD_DIR/PolicyEnforcerFunction/"

echo ""
echo "Build complete!"
echo "Run: sam local invoke ListAgentsFunction -e events/list_agents.json"
