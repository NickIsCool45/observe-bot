#!/usr/bin/env bash
# Run the trading desk

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 src/runner.py "$@"