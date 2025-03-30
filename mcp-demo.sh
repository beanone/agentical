#!/bin/bash

# Exit on error
set -e

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found in .venv"
    echo "Please create and set up the virtual environment first"
    exit 1
fi

echo "Running mcp example tools..."

# Run the demo (using proper module notation)
python -m examples.demos.mcp_demo

# Deactivate virtual environment
deactivate
