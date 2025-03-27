#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Source .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
else
    echo "No .env file found. You can create one with your API keys:"
    echo "OPENWEATHERMAP_API_KEY=your_key"
    echo "OPENAI_API_KEY=your_key"
fi

# Check for required API keys
if [ -z "$OPENWEATHERMAP_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo -e "\nMissing required API keys. Please either:"
    echo "1. Create a .env file with the required keys, or"
    echo "2. Export them in your shell:"
    echo "   export OPENWEATHERMAP_API_KEY=your_key"
    echo "   export OPENAI_API_KEY=your_key"
    exit 1
fi

# Run example tools
echo -e "\nRunning example tools..."
python3 -m examples.tools.examples 