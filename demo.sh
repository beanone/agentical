#!/bin/bash

# Set the path to the directory containing the MCP server
PYTHONPATH=src python test_mcp_provider.py "$@"
