"""Tools package for MCP Architecture.

This package contains tool implementations for the MCP plugin architecture.
"""

# Leave this file empty to avoid circular imports
# Tool and ToolParameter classes are defined in my_assistant.mcp.tools 

"""Example tools for the Agentical framework."""

from .weather_tool import create_weather_tool, weather_handler

__all__ = ["create_weather_tool", "weather_handler"] 