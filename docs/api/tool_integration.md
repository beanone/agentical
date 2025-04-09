# Tool Integration

## Table of Contents
- [Overview](#overview)
- [Tool Registry](#tool-registry)
- [Tool Validation](#tool-validation)
  - [Parameter Validation](#parameter-validation)
  - [Schema Validation](#schema-validation)
  - [Execution Validation](#execution-validation)
- [Tool Execution](#tool-execution)
  - [Basic Execution](#basic-execution)
  - [Advanced Execution](#advanced-execution)
- [Tool Conversion](#tool-conversion)
- [Tool Development](#tool-development)
  - [Creating a New Tool](#creating-a-new-tool)
  - [Tool Lifecycle](#tool-lifecycle)
- [Best Practices](#best-practices)

## Overview

This document covers how to work with MCP tools in Agentical, including tool registration, validation, execution, and development best practices.

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

## Tool Validation

### Parameter Validation

Tools implement comprehensive parameter validation:

```python
from typing import Any, Dict
from pydantic import BaseModel, Field, validator

class ToolParameter(BaseModel):
    """Base class for tool parameter validation."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if not provided")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Validation constraints")

    @validator('type')
    def validate_type(cls, v):
        """Validate parameter type."""
        valid_types = {'string', 'number', 'integer', 'boolean', 'array', 'object'}
        if v not in valid_types:
            raise ValueError(f"Invalid type: {v}. Must be one of {valid_types}")
        return v

    @validator('constraints')
    def validate_constraints(cls, v, values):
        """Validate parameter constraints based on type."""
        param_type = values.get('type')
        if param_type == 'string':
            valid_constraints = {'minLength', 'maxLength', 'pattern'}
        elif param_type in {'number', 'integer'}:
            valid_constraints = {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum'}
        elif param_type == 'array':
            valid_constraints = {'minItems', 'maxItems', 'uniqueItems'}
        else:
            valid_constraints = set()

        invalid = set(v.keys()) - valid_constraints
        if invalid:
            raise ValueError(f"Invalid constraints for type {param_type}: {invalid}")
        return v
```

### Schema Validation

Tool schemas are validated using JSON Schema:

```python
from jsonschema import validate, ValidationError

class ToolSchemaValidator:
    """Validates tool schemas against JSON Schema specification."""

    def validate_schema(self, schema: dict) -> None:
        """Validate a tool schema."""
        try:
            # Validate against JSON Schema draft-07
            validate(instance=schema, schema={
                "type": "object",
                "required": ["name", "description", "parameters"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "parameters": {
                        "type": "object",
                        "required": ["type", "properties"],
                        "properties": {
                            "type": {"type": "string", "enum": ["object"]},
                            "properties": {"type": "object"},
                            "required": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            })
        except ValidationError as e:
            raise ValueError(f"Invalid tool schema: {e.message}")
```

### Execution Validation

Tools validate execution context and parameters:

```python
class ToolExecutionValidator:
    """Validates tool execution context and parameters."""

    def validate_execution(
        self,
        tool: Tool,
        parameters: dict,
        context: dict | None = None
    ) -> None:
        """Validate tool execution parameters and context."""
        # Validate required parameters
        missing = set(tool.parameters.get('required', [])) - set(parameters.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Validate parameter types
        for name, value in parameters.items():
            param_schema = tool.parameters['properties'].get(name)
            if not param_schema:
                raise ValueError(f"Unknown parameter: {name}")

            self._validate_parameter_type(name, value, param_schema)

        # Validate execution context
        if context:
            self._validate_context(context)

    def _validate_parameter_type(
        self,
        name: str,
        value: Any,
        schema: dict
    ) -> None:
        """Validate parameter value against its schema."""
        param_type = schema.get('type')
        if param_type == 'string' and not isinstance(value, str):
            raise ValueError(f"Parameter {name} must be a string")
        elif param_type == 'number' and not isinstance(value, (int, float)):
            raise ValueError(f"Parameter {name} must be a number")
        elif param_type == 'integer' and not isinstance(value, int):
            raise ValueError(f"Parameter {name} must be an integer")
        elif param_type == 'boolean' and not isinstance(value, bool):
            raise ValueError(f"Parameter {name} must be a boolean")
        elif param_type == 'array' and not isinstance(value, list):
            raise ValueError(f"Parameter {name} must be an array")
        elif param_type == 'object' and not isinstance(value, dict):
            raise ValueError(f"Parameter {name} must be an object")
```

## Tool Execution

### Basic Execution

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

### Advanced Execution

Tools support advanced execution patterns:

```python
class ToolExecutor:
    """Handles advanced tool execution patterns."""

    async def execute_with_timeout(
        self,
        tool: Tool,
        timeout: float,
        **kwargs
    ) -> CallToolResult:
        """Execute a tool with timeout."""
        try:
            async with asyncio.timeout(timeout):
                return await execute_tool(tool, **kwargs)
        except asyncio.TimeoutError:
            return CallToolResult(
                success=False,
                error=f"Tool execution timed out after {timeout} seconds"
            )

    async def execute_with_retry(
        self,
        tool: Tool,
        max_retries: int = 3,
        **kwargs
    ) -> CallToolResult:
        """Execute a tool with retry logic."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await execute_tool(tool, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
        return CallToolResult(
            success=False,
            error=f"Tool execution failed after {max_retries} attempts: {last_error}"
        )
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

### Tool Lifecycle

Tools follow a defined lifecycle:

```python
class ToolLifecycleManager:
    """Manages tool lifecycle events."""

    async def initialize_tool(self, tool: Tool) -> None:
        """Initialize a tool before first use."""
        # Load resources
        # Validate configuration
        # Setup connections
        pass

    async def cleanup_tool(self, tool: Tool) -> None:
        """Cleanup tool resources."""
        # Close connections
        # Release resources
        # Save state if needed
        pass

    async def validate_tool(self, tool: Tool) -> None:
        """Validate tool state and configuration."""
        # Check dependencies
        # Verify permissions
        # Test connectivity
        pass
```

## Best Practices

1. **Tool Design**
   - Clear, concise descriptions
   - Well-defined parameter schemas
   - Proper error handling
   - Comprehensive documentation
   - Version compatibility
   - Backward compatibility

2. **Tool Implementation**
   - Async-first design
   - Proper resource management
   - Error handling and validation
   - Performance optimization
   - State management
   - Dependency injection

3. **Tool Registration**
   - Unique tool names
   - Proper server organization
   - Clear tool categorization
   - Version management
   - Dependency tracking
   - Lifecycle management

4. **Tool Testing**
   - Unit tests for each tool
   - Integration testing
   - Error case testing
   - Performance testing
   - State transition testing
   - Resource cleanup testing