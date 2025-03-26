"""Tool Registry for Simple Agentical Framework.

This module provides a registry for managing tool definitions.
"""

from typing import Dict, List, Any, Union
from agentical.core.types import Tool


class ToolRegistry:
    """Registry for managing tool definitions.
    
    The registry maintains a collection of tools that can be used by an agent.
    It ensures that tool names are unique and provides methods for retrieving
    tool definitions and converting them to provider-specific formats.
    """
    
    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, Tool] = {}
        
    def register_tool(self, tool: Union[Tool, Dict[str, Any]]) -> None:
        """Register a new tool in the registry.
        
        Args:
            tool: The tool definition to register (either a Tool object or dict)
            
        Raises:
            ValueError: If a tool with the same name already exists
        """
        # Convert dict to Tool if needed
        if isinstance(tool, dict):
            tool = Tool(**tool)
            
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
            
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Tool:
        """Get a tool definition by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool definition
            
        Raises:
            KeyError: If no tool with the given name exists
        """
        if name not in self._tools:
            raise KeyError(f"No tool named '{name}' is registered")
        return self._tools[name]
        
    def list_tools(self) -> List[Tool]:
        """Get a list of all registered tools.
        
        Returns:
            List of all registered tool definitions
        """
        return list(self._tools.values()) 