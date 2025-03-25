"""Tool Registry for Simple Agentical Framework.

This module provides a registry for managing tool definitions.
"""

from typing import Dict, List, Any, Union
from agentical.types import Tool


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
        
    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert registered tools to OpenAI's function format.
        
        Returns:
            List of tools in OpenAI's function format
        """
        openai_tools = []
        for tool in self._tools.values():
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Convert parameters
            for name, param in tool.parameters.items():
                openai_tool["function"]["parameters"]["properties"][name] = {
                    "type": param.type,
                    "description": param.description
                }
                if param.enum:
                    openai_tool["function"]["parameters"]["properties"][name]["enum"] = param.enum
                if param.required:
                    openai_tool["function"]["parameters"]["required"].append(name)
                    
            openai_tools.append(openai_tool)
            
        return openai_tools
        
    def to_anthropic_format(self) -> List[Dict[str, Any]]:
        """Convert registered tools to Anthropic's tool format.
        
        Returns:
            List of tools in Anthropic's tool format
        """
        anthropic_tools = []
        for tool in self._tools.values():
            anthropic_tool = {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Convert parameters
            for name, param in tool.parameters.items():
                anthropic_tool["parameters"]["properties"][name] = {
                    "type": param.type,
                    "description": param.description
                }
                if param.enum:
                    anthropic_tool["parameters"]["properties"][name]["enum"] = param.enum
                if param.required:
                    anthropic_tool["parameters"]["required"].append(name)
                    
            anthropic_tools.append(anthropic_tool)
            
        return anthropic_tools 