# Agentical

A simple, flexible framework for building tool-enabled AI agents in Python. Agentical provides a clean, type-safe interface for creating AI agents that can use tools and interact with various LLM providers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- 🔌 **LLM Integration**: Built-in support for OpenAI and Anthropic, with an extensible provider system
- 🛠️ **Flexible Tool System**: Easy-to-use interface for creating and managing tools
- 🔒 **Type Safety**: Full type hints and runtime type checking with Pydantic
- 🧩 **Modular Design**: Easily extend with new providers and tools
- 🔄 **Async First**: Built for asynchronous operations from the ground up
- 📝 **Comprehensive Logging**: Detailed logging for debugging and monitoring
- 🧪 **Testing Support**: Extensive test utilities and mocking support

## Installation

```bash
# Basic installation (core functionality only)
pip install agentical

# With LLM support (OpenAI and Anthropic)
pip install agentical[llm]

# With development tools
pip install agentical[dev]
```

## Quick Start

First, install Agentical with LLM support:
```bash
pip install agentical[llm]
```

1. Set up your environment variables:

```bash
# .env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

2. Create a tool-enabled agent:

```python
import os
from agentical import ToolRegistry, ToolExecutor, tool
from agentical.core import ProviderConfig
from agentical.providers.llm import LLMToolIntegration

# Define a simple tool
@tool(
    name="calculator",
    description="Performs basic arithmetic operations",
    parameters={
        "operation": "The operation to perform (add, subtract, multiply, divide)",
        "numbers": "List of numbers to operate on"
    }
)
def calculator(operation: str, numbers: list[float]) -> float:
    """A simple calculator tool that performs basic arithmetic."""
    if operation == "add":
        return sum(numbers)
    elif operation == "multiply":
        result = 1
        for num in numbers:
            result *= num
        return result
    elif operation == "subtract":
        if not numbers:
            return 0
        result = numbers[0]
        for num in numbers[1:]:
            result -= num
        return result
    elif operation == "divide":
        if not numbers:
            return 0
        result = numbers[0]
        for num in numbers[1:]:
            if num == 0:
                raise ValueError("Cannot divide by zero")
            result /= num
        return result
    else:
        raise ValueError(f"Unknown operation: {operation}")

def main():
    # Set up tool registry and executor
    registry = ToolRegistry()
    registry.register_tool(calculator)
    executor = ToolExecutor(registry)
    
    # Configure the LLM provider
    provider_config = ProviderConfig(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model="claude-3-sonnet-20240229"
    )
    
    # Create LLM integration
    integration = LLMToolIntegration(
        registry=registry,
        executor=executor,
        provider_config=provider_config,
        model_provider="anthropic"
    )
    
    # Run a conversation with tool support
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can perform calculations."
        },
        {
            "role": "user",
            "content": "Can you multiply 23 and 45?"
        }
    ]
    
    # The run_conversation method is async, but we can run it in a sync context
    import asyncio
    response = asyncio.run(integration.run_conversation(messages))
    print(response)

if __name__ == "__main__":
    main()
```

This example demonstrates:
1. Creating and registering a tool
2. Setting up the tool executor
3. Configuring an LLM provider
4. Using `LLMToolIntegration` to combine tools with LLM capabilities

## Architecture

Agentical is built around these core components:

- **Providers**: Interface with LLM services (OpenAI, Anthropic, etc.)
- **Tools**: Executable functions that agents can use
- **Registry**: Manages available tools and their metadata
- **Executor**: Handles tool execution and response processing

### Provider System

The provider system is designed to be extensible and configurable:

```python
from agentical.core import ProviderSettings, ProviderConfig

# Global settings for all providers
settings = ProviderSettings(
    openai_model="gpt-4-turbo-preview",
    anthropic_model="claude-3-sonnet-20240229"
)

# Provider-specific configuration
config = ProviderConfig.from_settings("openai", settings)
```

### Tool System

Tools are defined using a simple decorator pattern:

```python
from agentical import tool

@tool(
    name="calculator",
    description="Performs basic arithmetic operations",
    parameters={
        "operation": "The operation to perform (add, subtract, multiply, divide)",
        "numbers": "List of numbers to operate on"
    }
)
def calculator(operation: str, numbers: list[float]) -> float:
    """A simple calculator tool that performs basic arithmetic."""
    if operation == "add":
        return sum(numbers)
    # ... other operations
```

## Development

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentical.git
cd agentical
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
./run_tests.sh

# Run only integration tests
./run_integration_tests.sh

# Run with coverage
pytest --cov=agentical
```

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Linting and static analysis
- **MyPy**: Type checking
- **Pre-commit**: Automated checks before commits

Run the pre-commit hooks:
```bash
pre-commit run --all-files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

Please ensure your PR:
- Includes tests for new features
- Updates documentation as needed
- Follows the project's code style
- Includes a clear description of changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to all contributors
- Inspired by various agent frameworks in the Python ecosystem 