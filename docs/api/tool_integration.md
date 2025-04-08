# Tool Integration

This document covers how to work with MCP tools in Agentical.

## Tool Registry

The `ToolRegistry` manages tool registration and lookup:

```python
from mcp.types import Tool as MCPTool

class ToolRegistry:
    def register_server_tools(self, server_name: str, tools: list[MCPTool]) -> None:
        """Register tools for a specific server.

        Args:
            server_name: Name of the server providing the tools
            tools: List of tools to register
        """
        pass

    def get_all_tools(self) -> list[MCPTool]:
        """Get all registered tools.

        Returns:
            List of all registered tools
        """
        pass

    def get_server_tools(self, server_name: str) -> list[MCPTool]:
        """Get tools for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of tools registered for the server
        """
        pass
```

## Tool Execution

Tools are executed through the `execute_tool` callback provided to the LLM backend:

```python
from mcp.types import Tool, CallToolResult

async def execute_tool(tool: Tool, **kwargs) -> CallToolResult:
    """Execute a tool with the given parameters.

    Args:
        tool: The tool to execute
        **kwargs: Tool-specific parameters

    Returns:
        The result of the tool execution
    """
    pass
```

### Example Tool Execution

```python
# Example tool execution in an LLM backend
async def process_query(self, query: str, tools: list[Tool], execute_tool: callable):
    # LLM decides to use a tool
    result = await execute_tool(
        tool=tools[0],
        param1="value1",
        param2="value2"
    )

    # Process the result
    if result.success:
        # Handle successful execution
        response = result.output
    else:
        # Handle execution error
        error = result.error
```

## Tool Conversion

Different LLM backends may require tools to be formatted in specific ways. The `convert_tools` method handles this:

```python
def convert_tools(self, tools: list[MCPTool]) -> list[MCPTool]:
    """Convert MCP tools to the format expected by this LLM.

    Example for OpenAI format:
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        }
    }
    """
    pass
```

### Example Tool Conversion

```python
# Example for OpenAI backend
def convert_tools(self, tools: list[MCPTool]) -> list[dict]:
    converted = []
    for tool in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        })
    return converted
```

## Tool Development

### Creating a New Tool

1. Define the tool schema:
```python
from mcp.types import Tool

weather_tool = Tool(
    name="get_weather",
    description="Get current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or coordinates"
            }
        },
        "required": ["location"]
    }
)
```

2. Implement the tool execution:
```python
async def execute_weather_tool(location: str) -> dict:
    """Get weather information for a location."""
    # Implementation here
    pass
```

3. Register with MCP server:
```python
class WeatherServer(MCPServer):
    def __init__(self):
        super().__init__()
        self.register_tool(
            weather_tool,
            execute_weather_tool
        )
```

## Best Practices

1. **Tool Design**
   - Clear, concise descriptions
   - Well-defined parameter schemas
   - Proper error handling
   - Comprehensive documentation

2. **Tool Implementation**
   - Async-first design
   - Proper resource management
   - Error handling and validation
   - Performance optimization

3. **Tool Registration**
   - Unique tool names
   - Proper server organization
   - Clear tool categorization
   - Version management

4. **Tool Testing**
   - Unit tests for each tool
   - Integration testing
   - Error case testing
   - Performance testing