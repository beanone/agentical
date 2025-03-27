#!/bin/bash

# Run tests
echo "Running tests..."
python3 -m pytest tests/core tests/examples tests/providers -v
