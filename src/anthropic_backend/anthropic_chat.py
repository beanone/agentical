"""Anthropic implementation for chat interactions."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Callable
import traceback
from anthropic import AsyncAnthropic

from agentical.core.llm_backend import LLMBackend
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult
import re

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)

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
            self.model = SchemaAdapter.DEFAULT_MODEL
            self.schema_adapter = SchemaAdapter()
            logger.debug(f"Initialized Anthropic client with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    def convert_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Anthropic format.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in Anthropic format
        """
        return self.schema_adapter.convert_mcp_tools_to_anthropic(tools)

    
    @staticmethod
    def extract_answer(text: str) -> str:
        """Extract the content within <answer> tags, or return the full text if not found."""
        match = re.search(r'<answer>(.*?)</answer>', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
    
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
                # Get response from Anthropic
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
                        answer = self.extract_answer(block.text)
                        if answer:
                            result_text.append(answer)
                        else:
                            result_text.append(block.text)
                    elif block.type == "tool_use":
                        has_tool_calls = True
                        try:
                            logger.debug(f"Executing tool: {block.name}")
                            logger.debug(f"Tool arguments: {json.dumps(block.input, indent=2)}")
                            # Execute the tool
                            tool_response = await execute_tool(
                                block.name,
                                block.input
                            )
                            logger.debug(f"Tool response: {tool_response}")
                            
                            # Add tool call and response to messages
                            anthropic_messages.append(
                                self.schema_adapter.create_assistant_message(
                                    f"I'll use the {block.name} tool with input: {json.dumps(block.input)}"
                                )
                            )
                            anthropic_messages.append(
                                self.schema_adapter.create_tool_response_message(
                                    tool_name=block.name,
                                    result=tool_response
                                )
                            )
                        except Exception as e:
                            logger.error(f"Tool execution failed: {str(e)}")
                            anthropic_messages.append(
                                self.schema_adapter.create_tool_response_message(
                                    tool_name=block.name,
                                    error=str(e)
                                )
                            )
                
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