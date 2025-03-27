#!/bin/bash

# Run tests
echo "Running integration tests..."
pytest -v -s -m "integration"
