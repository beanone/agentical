# Agentical

A simple, flexible framework for building tool-enabled AI agents. This library provides the core infrastructure needed to create, manage, and execute tools that can be used by AI agents.

## Features

- 🛠️ **Modular Tool System**: Easy-to-use framework for creating and managing tools
- 🔌 **Extensible Design**: Simple interface for adding new tools
- 🤖 **LLM Integration**: Optional support for OpenAI's API
- 🔒 **Type Safety**: Full type hints and runtime validation
- 📚 **Documentation**: Comprehensive docstrings and examples

## Installation

Install the base package:
```bash
pip install agentical
```

Install with OpenAI integration:
```bash
pip install "agentical[openai]"
```

Install with development dependencies:
```bash
pip install "agentical[dev]"
```

Install with example dependencies:
```bash
pip install "agentical[examples]"
```

## Quick Start

```python
import asyncio
from agentical.core.registry import ToolRegistry
from agentical.core.executor import ToolExecutor
from agentical.types import Tool, ToolParameter

# Define a simple tool
def create_hello_tool() -> Tool:
    return Tool(
        name="hello",
        description="Say hello to someone",
        parameters={
            "name": ToolParameter(
                type="string",
                description="Name to greet",
                required=True
            )
        }
    )

# Create a handler
async def hello_handler(params: dict) -> str:
    name = params.get("name", "World")
    return f"Hello, {name}!"

# Use the tool
async def main():
    # Create registry and register tool
    registry = ToolRegistry()
    hello_tool = create_hello_tool()
    registry.register_tool(hello_tool)
    
    # Create executor and register handler
    executor = ToolExecutor(registry)
    executor.register_handler("hello", hello_handler)
    
    # Execute the tool
    result = await executor.execute_tool(
        "hello", 
        {"name": "Alice"}
    )
    print(result)  # Prints: Hello, Alice!

asyncio.run(main())
```

## Core Components

### Tool Registry

The `ToolRegistry` manages tool definitions and ensures they are valid:

```python
from agentical.core.registry import ToolRegistry
from agentical.types import Tool, ToolParameter

# Create a tool definition
my_tool = Tool(
    name="my_tool",
    description="Do something useful",
    parameters={
        "param1": ToolParameter(
            type="string",
            description="First parameter",
            required=True
        )
    }
)

# Register the tool
registry = ToolRegistry()
registry.register_tool(my_tool)
```

### Tool Executor

The `ToolExecutor` handles tool execution and parameter validation:

```python
from agentical.core.executor import ToolExecutor

# Create executor
executor = ToolExecutor(registry)

# Register handler
async def my_handler(params: dict) -> str:
    return f"Got params: {params}"

executor.register_handler("my_tool", my_handler)

# Execute tool
result = await executor.execute_tool("my_tool", {"param1": "value1"})
```

### LLM Integration (Optional)

Optional integration with OpenAI's API (requires `agentical[openai]`):

```python
from agentical.core.integration import LLMToolIntegration

# Create integration
integration = LLMToolIntegration(registry, executor)

# Run conversation
messages = [
    {"role": "user", "content": "Use my_tool with param1=test"}
]
response = await integration.run_conversation(messages)
```

## Examples

Check out the `examples/` directory for complete examples:

- `examples/tools/`: Example tool implementations
  - Weather tool using OpenWeatherMap API
  - Calculator tool for safe expression evaluation
  - Filesystem tool for safe file operations
- `examples/demos/`: Example applications
  - CLI demo with multiple tools
  - Chat interface with LLM integration

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentical.git
cd agentical
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev,examples]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

5. Run tests:
```bash
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 