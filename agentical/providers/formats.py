"""Tool Definition Layer for Simple Agentical Framework.

This module provides base classes and utilities for defining tools.
"""

from typing import Dict, Any
from agentical.core.types import Tool


def to_openai_format(tool: Tool) -> Dict[str, Any]:
    """Convert tool definition to OpenAI function format.
    
    Args:
        tool: The tool definition to convert
        
    Returns:
        Dict representation compatible with OpenAI's function calling format
    """
    properties = {}
    required = []
    
    for name, param in tool.parameters.items():
        properties[name] = {
            "type": param.type,
            "description": param.description
        }
        if hasattr(param, "enum") and param.enum:
            properties[name]["enum"] = param.enum
        if param.required:
            required.append(name)
            
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }
    
def to_anthropic_format(tool: Tool) -> Dict[str, Any]:
    """Convert tool definition to Anthropic's tool format.
    
    Args:
        tool: The tool definition to convert
        
    Returns:
        Dict representation compatible with Anthropic's tool calling format
    """
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    for name, param in tool.parameters.items():
        schema["properties"][name] = {
            "type": param.type,
            "description": param.description
        }
        if hasattr(param, "enum") and param.enum:
            schema["properties"][name]["enum"] = param.enum
        if param.required:
            schema["required"].append(name)
            
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": schema
    } 