#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests
echo "Running tests..."
python3 -m pytest tests/core tests/examples tests/providers -v
