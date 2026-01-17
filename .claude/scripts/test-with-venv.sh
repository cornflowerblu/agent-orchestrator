#!/bin/bash
# Activate virtual environment and run pytest with coverage

set -e  # Exit on error

# Project root
PROJECT_ROOT="/Users/rurich/Development/agent-orchestrator"

# Activate virtual environment
source "${PROJECT_ROOT}/.venv/bin/activate"

# Run pytest with coverage
# Excludes integration tests by default (they require AWS deployment)
pytest --cov=src --cov-report=term-missing -m "not integration" "$@"
