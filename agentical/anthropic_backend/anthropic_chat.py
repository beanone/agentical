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

# Default model for Anthropic API
DEFAULT_MODEL = "claude-3-opus-20240229"

class AnthropicBackend(LLMBackend):
    """Anthropic implementation for chat interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Anthropic backend.
        
        Args:
            api_key: Optional Anthropic API key. If not provided, will look for ANTHROPIC_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided or found in environment
        """
        logger.debug("Initializing Anthropic backend")
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Please provide it or set in environment.")
            
        try:
            self.client = AsyncAnthropic(api_key=api_key)
            self.model = DEFAULT_MODEL
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
            logger.debug(f"Processing query: {query}")
            logger.debug(f"Number of tools available: {len(tools)}")
            if context:
                logger.debug(f"Context messages: {len(context)}")
            
            # Initialize or use existing conversation context
            messages = list(context) if context else []
            
            # Extract system message if present and convert other messages
            system_content = None
            anthropic_messages = []
            
            for msg in messages:
                logger.debug(f"Processing message with role: {msg['role']}")
                if msg["role"] == "system":
                    system_content = msg["content"]
                    logger.debug("Found system message")
                elif msg["role"] == "user":
                    anthropic_messages.append(self.schema_adapter.create_user_message(msg["content"]))
                elif msg["role"] == "assistant":
                    anthropic_messages.append(self.schema_adapter.create_assistant_message(msg["content"]))
            
            # Add the new user query
            anthropic_messages.append(self.schema_adapter.create_user_message(query))
            
            # Convert tools to Anthropic format
            anthropic_tools = self.schema_adapter.convert_mcp_tools_to_anthropic(tools)
            logger.debug(f"Converted tools: {json.dumps(anthropic_tools, indent=2)}")

            # Set default system content if none provided
            if not system_content:
                system_content = """
                You are an AI assistant. When responding, please follow these guidelines:
                1. If you need to think through the problem, enclose your reasoning within <thinking> tags.
                2. Always provide your final answer within <answer> tags.
                3. If no reasoning is needed, you can omit the <thinking> tags.
                """
            
            # Create system message content blocks if we have system content
            system_blocks = self.schema_adapter.create_system_message(system_content) if system_content else None
            
            while True:
                logger.debug("Making API call to Anthropic")
                logger.debug(f"system_blocks: {json.dumps(system_blocks) if system_blocks else None}")
                logger.debug(f"messages: {json.dumps(anthropic_messages)}")
                logger.debug(f"tools: {json.dumps(anthropic_tools)}")
                
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
                
                logger.debug(f"Final API kwargs: {json.dumps(kwargs, default=str)}")
                response = await self.client.messages.create(**kwargs)
                logger.debug("Received response from Anthropic")
                
                # Process content blocks
                result_text = []
                has_tool_calls = False
                
                logger.debug(f"Processing response content blocks: {len(response.content)} blocks")
                for block in response.content:
                    logger.debug(f"Processing content block type: {block.type}")
                    logger.debug(f"Processing content block: {block}")
                    
                    if block.type == "text":
                        answer = self.schema_adapter.extract_answer(block.text)
                        result_text.append(answer)
                
                # Extract and handle tool calls
                tool_calls = self.schema_adapter.extract_tool_calls(response)
                if tool_calls:
                    has_tool_calls = True
                    for tool_name, tool_params in tool_calls:
                        await self._handle_tool_use(tool_name, tool_params, execute_tool, anthropic_messages)
                
                if not has_tool_calls:
                    result = " ".join(result_text) or "No response generated"
                    logger.debug(f"Final response: {result}")
                    return result
                
                logger.debug("Continuing conversation with tool results")
            
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Error in Anthropic conversation: {str(e)}")
            logger.error(f"Stacktrace: {stacktrace}")
            raise ValueError(f"Error in Anthropic conversation: {str(e)}")
            
    async def _handle_tool_use(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        execute_tool: Callable[[str, Dict[str, Any]], CallToolResult],
        anthropic_messages: List[Dict[str, Any]]
    ) -> None:
        """Handle a tool use from Anthropic's response.
        
        Args:
            tool_name: Name of the tool to execute
            tool_params: Parameters for the tool
            execute_tool: Function to execute the tool
            anthropic_messages: List of messages to append tool results to
        """
        try:
            logger.debug(f"Executing tool: {tool_name}")
            logger.debug(f"Tool arguments: {json.dumps(tool_params, indent=2)}")
            
            tool_response = await execute_tool(tool_name, tool_params)
            logger.debug(f"Tool response: {tool_response}")
            
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