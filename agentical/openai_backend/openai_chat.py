"""OpenAI implementation for chat interactions."""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Callable

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from agentical.api.llm_backend import LLMBackend
from agentical.utils.log_utils import redact_sensitive_data, sanitize_log_message
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
            
        Environment Variables:
            OPENAI_API_KEY: API key for OpenAI
            OPENAI_MODEL: Model to use (defaults to DEFAULT_MODEL if not set)
        """
        logger.info("Initializing OpenAI backend")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Please provide it or set in environment.")
            
        try:
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL)
            logger.info("Initialized OpenAI client", extra=redact_sensitive_data({
                "model": self.model,
                "api_key_length": len(api_key)
            }))
        except Exception as e:
            error_msg = sanitize_log_message(f"Failed to initialize OpenAI client: {str(e)}")
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def _format_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Format tools for OpenAI's function calling format.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in OpenAI function format
        """
        start_time = time.time()
        formatted_tools = []
        
        try:
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
                
                logger.debug("Formatted tool", extra={
                    "tool_name": tool.name,
                    "has_parameters": bool(schema)
                })
            
            duration = time.time() - start_time
            logger.debug("Tool formatting completed", extra={
                "num_tools": len(tools),
                "duration_ms": int(duration * 1000)
            })
            return formatted_tools
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Tool formatting failed", extra={
                "error": str(e),
                "duration_ms": int(duration * 1000)
            })
            raise

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
        start_time = time.time()
        try:
            logger.info("Processing query", extra=redact_sensitive_data({
                "query": query,
                "num_tools": len(tools),
                "has_context": context is not None
            }))
            
            # Initialize or use existing conversation context
            messages = list(context) if context else []
            messages.append({"role": "user", "content": query})
            
            # Convert tools to OpenAI format
            formatted_tools = self._format_tools(tools)
            
            while True:  # Continue until we get a response without tool calls
                # Get response from OpenAI
                api_start = time.time()
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=formatted_tools,
                    tool_choice="auto"
                )
                api_duration = time.time() - api_start
                logger.debug("OpenAI API call completed", extra={
                    "duration_ms": int(api_duration * 1000)
                })
                
                message = response.choices[0].message
                
                # If no tool calls, return the final response
                if not message.tool_calls:
                    duration = time.time() - start_time
                    logger.info("Query completed without tool calls", extra={
                        "duration_ms": int(duration * 1000)
                    })
                    return message.content or "No response generated"
                
                # Handle each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse tool arguments", extra={
                            "error": str(e),
                            "tool_name": function_name,
                            "raw_args": sanitize_log_message(tool_call.function.arguments)
                        })
                        continue
                    
                    # Execute the tool
                    tool_start = time.time()
                    try:
                        function_response = await execute_tool(function_name, function_args)
                        tool_duration = time.time() - tool_start
                        logger.debug("Tool execution completed", extra={
                            "tool_name": function_name,
                            "duration_ms": int(tool_duration * 1000)
                        })
                    except Exception as e:
                        tool_duration = time.time() - tool_start
                        logger.error("Tool execution failed", extra={
                            "tool_name": function_name,
                            "error": sanitize_log_message(str(e)),
                            "duration_ms": int(tool_duration * 1000)
                        })
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
                
                # Continue the loop to let the model make more tool calls
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = sanitize_log_message(f"Error in OpenAI conversation: {str(e)}")
            logger.error(error_msg, extra={
                "error": str(e),
                "duration_ms": int(duration * 1000)
            }, exc_info=True)
            raise ValueError(error_msg)
        finally:
            duration = time.time() - start_time
            logger.info("Query processing completed", extra={
                "duration_ms": int(duration * 1000)
            })

    def convert_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI format.
        
        This is a public wrapper around _format_tools for the interface.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in OpenAI format
        """
        return self._format_tools(tools) 