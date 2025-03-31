"""OpenAI implementation for chat interactions."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Callable

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from agentical.api.llm_backend import LLMBackend
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)

class OpenAIBackend(LLMBackend):
    """OpenAI implementation for chat interactions."""
    
    DEFAULT_MODEL = "gpt-4-turbo-preview"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI backend.
        
        Args:
            api_key: Optional OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided or found in environment
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Please provide it or set in environment.")
            
        try:
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = self.DEFAULT_MODEL
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    def _format_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Format tools for OpenAI's function calling format.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in OpenAI function format
        """
        formatted_tools = []
        for tool in tools:
            # Get the tool's schema directly from the MCP Tool
            schema = tool.parameters if hasattr(tool, 'parameters') else {}
            
            # Create OpenAI function format
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools

    async def process_query(
        self,
        query: str,
        tools: List[MCPTool],
        execute_tool: Callable[[str, Dict[str, Any]], CallToolResult],
        context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Process a query using OpenAI with the given tools.
        
        Args:
            query: The user's query
            tools: List of available MCP tools
            execute_tool: Function to execute a tool call
            context: Optional conversation context
            
        Returns:
            Generated response from OpenAI
            
        Raises:
            ValueError: If there's an error communicating with OpenAI
        """
        try:
            # Initialize or use existing conversation context
            messages = list(context) if context else []
            messages.append({"role": "user", "content": query})
            
            # Convert tools to OpenAI format
            formatted_tools = self._format_tools(tools)
            
            # Get response from OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=formatted_tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check if the model wanted to call a function
            if message.tool_calls:
                # Handle each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        continue
                    
                    # Execute the tool
                    try:
                        function_response = await execute_tool(function_name, function_args)
                    except Exception as e:
                        logger.error(f"Tool execution failed: {str(e)}")
                        function_response = f"Error: {str(e)}"
                    
                    # Add tool call and response to conversation
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(function_response)
                    })
                
                # Get final response after tool calls
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=formatted_tools,
                    tool_choice="auto"
                )
                
                return final_response.choices[0].message.content or "No response generated"
            
            return message.content or "No response generated"
            
        except Exception as e:
            raise ValueError(f"Error in OpenAI conversation: {str(e)}")

    def convert_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI format.
        
        This is a public wrapper around _format_tools for the interface.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in OpenAI format
        """
        return self._format_tools(tools) 