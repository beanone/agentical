"""Anthropic implementation for chat interactions."""

import json
import logging
import os
import traceback
from typing import Any, Dict, List, Optional, Callable

from anthropic import AsyncAnthropic

from agentical.api.llm_backend import LLMBackend
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)

class AnthropicBackend(LLMBackend):
    """Anthropic implementation for chat interactions."""
    
    DEFAULT_MODEL = "claude-3-opus-20240229"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Anthropic backend.
        
        Args:
            api_key: Optional Anthropic API key. If not provided, will look for ANTHROPIC_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided or found in environment
            
        Environment Variables:
            ANTHROPIC_API_KEY: API key for Anthropic
            ANTHROPIC_MODEL: Model to use (defaults to DEFAULT_MODEL if not set)
        """
        logger.debug("Initializing Anthropic backend")
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Please provide it or set in environment.")
            
        try:
            self.client = AsyncAnthropic(api_key=api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL)
            self.schema_adapter = SchemaAdapter()
            logger.debug(f"Initialized Anthropic client with model: {self.model}")
        except Exception as e:
            error_msg = f"Failed to initialize Anthropic client: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def convert_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Anthropic format.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in Anthropic format
        """
        return self.schema_adapter.convert_mcp_tools_to_anthropic(tools)
    
    async def process_query(
        self,
        query: str,
        tools: List[MCPTool],
        execute_tool: Callable[[str, Dict[str, Any]], CallToolResult],
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Process a query using Anthropic with the given tools.
        
        Args:
            query: The user's query
            tools: List of available MCP tools
            execute_tool: Function to execute a tool call
            context: Optional conversation context
            
        Returns:
            Generated response from Anthropic
            
        Raises:
            ValueError: If there's an error communicating with Anthropic
        """
        try:
            # Initialize or use existing conversation context
            messages = list(context) if context else []
            
            # Extract system message if present and convert other messages
            system_content = None
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    anthropic_messages.append(self.schema_adapter.create_user_message(msg["content"]))
                elif msg["role"] == "assistant":
                    anthropic_messages.append(self.schema_adapter.create_assistant_message(msg["content"]))
            
            # Add the new user query
            anthropic_messages.append(self.schema_adapter.create_user_message(query))
            
            # Convert tools to Anthropic format
            anthropic_tools = self.schema_adapter.convert_mcp_tools_to_anthropic(tools)

            # Set default system content if none provided
            if not system_content:
                system_content = """You are an AI assistant. When responding, please follow these guidelines:
                1. If you need to think through the problem, enclose your reasoning within <thinking> tags.
                2. Always provide your final answer within <answer> tags.
                3. If no reasoning is needed, you can omit the <thinking> tags."""
            
            # Create system message content blocks
            system_blocks = self.schema_adapter.create_system_message(system_content) if system_content else None
            
            while True:  # Continue until we get a response without tool calls
                # Prepare API call parameters
                kwargs = {
                    "model": self.model,
                    "messages": anthropic_messages,
                    "tools": anthropic_tools,
                    "max_tokens": 4096,
                    "tool_choice": {
                        "type": "auto",
                        "disable_parallel_tool_use": True
                    }
                }
                if system_blocks:
                    kwargs["system"] = system_blocks
                
                # Get response from Anthropic
                response = await self.client.messages.create(**kwargs)
                
                # Extract tool calls
                tool_calls = self.schema_adapter.extract_tool_calls(response)
                
                # If no tool calls, return the final response
                if not tool_calls:
                    result_text = []
                    for block in response.content:
                        if block.type == "text":
                            answer = self.schema_adapter.extract_answer(block.text)
                            result_text.append(answer)
                    return " ".join(result_text) or "No response generated"
                
                # Handle each tool call
                for tool_name, tool_params in tool_calls:
                    try:
                        # Execute the tool
                        tool_response = await execute_tool(tool_name, tool_params)
                        
                        # Add tool call and response to messages
                        anthropic_messages.append(
                            self.schema_adapter.create_assistant_message(
                                f"I'll use the {tool_name} tool with input: {json.dumps(tool_params)}"
                            )
                        )
                        anthropic_messages.append(
                            self.schema_adapter.create_tool_response_message(
                                tool_name=tool_name,
                                result=tool_response
                            )
                        )
                    except Exception as e:
                        logger.error(f"Tool execution failed: {str(e)}")
                        anthropic_messages.append(
                            self.schema_adapter.create_tool_response_message(
                                tool_name=tool_name,
                                error=str(e)
                            )
                        )
                
                # Continue the loop to handle more tool calls
                
        except Exception as e:
            logger.error(f"Error in Anthropic conversation: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            raise ValueError(f"Error in Anthropic conversation: {str(e)}") 