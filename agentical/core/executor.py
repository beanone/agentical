"""Tool Executor for Simple Agentical Framework.

This module provides the executor for running tools with parameter validation.
"""

from typing import Dict, Any, Callable, Awaitable, Optional
from agentical.types import Tool, ToolResult, ToolHandler
from agentical.core.registry import ToolRegistry


class ToolExecutionError(Exception):
    """Raised when there is an error executing a tool."""
    pass


class ToolExecutor:
    """Executor for running tools with parameter validation.
    
    The executor maintains a mapping of tool names to their handlers and provides
    methods for registering handlers and executing tools with validated parameters.
    """
    
    def __init__(self, registry: ToolRegistry) -> None:
        """Initialize a tool executor.
        
        Args:
            registry: The tool registry containing tool definitions
        """
        self._registry = registry
        self._handlers: Dict[str, ToolHandler] = {}
        
    def register_handler(
        self, 
        name: str, 
        handler: Callable[[Dict[str, Any]], Awaitable[ToolResult]]
    ) -> None:
        """Register a handler for a tool.
        
        Args:
            name: The name of the tool
            handler: Async function that implements the tool's functionality
            
        Raises:
            KeyError: If no tool with the given name exists in the registry
        """
        # Verify tool exists in registry
        self._registry.get_tool(name)
        self._handlers[name] = handler
        
    async def execute_tool(
        self, 
        name: str, 
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool with the given parameters.
        
        Args:
            name: The name of the tool to execute
            parameters: Parameters to pass to the tool handler
            
        Returns:
            The result from the tool handler
            
        Raises:
            KeyError: If no tool with the given name exists
            ToolExecutionError: If the tool has no registered handler
            ToolExecutionError: If required parameters are missing
            ToolExecutionError: If the handler raises an exception
        """
        # Get tool definition
        tool = self._registry.get_tool(name)
        
        # Get handler
        handler = self._handlers.get(name)
        if handler is None:
            raise ToolExecutionError(f"No handler registered for tool '{name}'")
            
        # Validate parameters
        self._validate_parameters(tool, parameters)
        
        try:
            # Execute handler
            return await handler(parameters)
        except Exception as e:
            raise ToolExecutionError(f"Error executing tool '{name}': {str(e)}") from e
            
    def _validate_parameters(self, tool: Tool, parameters: Dict[str, Any]) -> None:
        """Validate parameters against tool definition.
        
        Args:
            tool: The tool definition
            parameters: Parameters to validate
            
        Raises:
            ToolExecutionError: If required parameters are missing
        """
        # Check for missing required parameters
        for name, param in tool.parameters.items():
            if param.required and name not in parameters:
                raise ToolExecutionError(
                    f"Missing required parameter '{name}' for tool '{tool.name}'"
                ) 