"""Anthropic implementation for chat interactions."""

import json
import logging
import os
import time
import traceback
from collections.abc import Callable
from typing import Any

import anthropic
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool

from agentical.api.llm_backend import LLMBackend
from agentical.utils.log_utils import sanitize_log_message

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)


class AnthropicBackend(LLMBackend):
    """Anthropic implementation for chat interactions."""

    DEFAULT_MODEL = "claude-3-opus-20240229"

    def __init__(self, api_key: str | None = None):
        """Initialize the Anthropic backend.

        Args:
            api_key: Optional Anthropic API key. If not provided, will look for 
                ANTHROPIC_API_KEY env var.

        Raises:
            ValueError: If API key is not provided or found in environment

        Environment Variables:
            ANTHROPIC_API_KEY: API key for Anthropic
            ANTHROPIC_MODEL: Model to use (defaults to DEFAULT_MODEL if not set)
        """
        logger.info("Initializing Anthropic backend")
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Please provide it or set in environment."
            )

        try:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL)
            self.schema_adapter = SchemaAdapter()
            logger.info(
                "Initialized Anthropic client",
                extra={"model": self.model, "api_key_length": len(api_key)},
            )
        except Exception as e:
            error_msg = sanitize_log_message(
                f"Failed to initialize Anthropic client: {e!s}"
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def convert_tools(self, tools: list[MCPTool]) -> list[dict[str, Any]]:
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
        tools: list[MCPTool],
        execute_tool: Callable[[str, dict[str, Any]], CallToolResult],
        context: list[dict[str, Any]] | None = None,
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
        start_time = time.time()
        try:
            logger.info(
                "Processing query",
                extra={
                    "query": query,
                    "num_tools": len(tools),
                    "has_context": context is not None,
                },
            )
            # Initialize or use existing conversation context
            messages = list(context) if context else []

            # Extract system message if present and convert other messages
            system_content = None
            anthropic_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    anthropic_messages.append(
                        self.schema_adapter.create_user_message(msg["content"])
                    )
                elif msg["role"] == "assistant":
                    anthropic_messages.append(
                        self.schema_adapter.create_assistant_message(msg["content"])
                    )

            # Add the new user query
            anthropic_messages.append(self.schema_adapter.create_user_message(query))

            # Convert tools to Anthropic format
            anthropic_tools = self.schema_adapter.convert_mcp_tools_to_anthropic(tools)

            # Set default system content if none provided
            if not system_content:
                system_content = (
                    "You are an AI assistant. When responding, please follow these "
                    "guidelines:\n"
                    "1. If you need to think through the problem, enclose your reasoning "
                    "within <thinking> tags.\n"
                    "2. Always provide your final answer within <answer> tags.\n"
                    "3. If no reasoning is needed, you can omit the <thinking> tags."
                )

            # Create system message content blocks
            system_blocks = (
                self.schema_adapter.create_system_message(system_content)
                if system_content
                else None
            )

            while True:  # Continue until we get a response without tool calls
                # Prepare API call parameters
                kwargs = {
                    "model": self.model,
                    "messages": anthropic_messages,
                    "tools": anthropic_tools,
                    "max_tokens": 4096,
                    "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
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
                        tool_start_time = time.time()
                        tool_response = await execute_tool(tool_name, tool_params)
                        tool_duration = time.time() - tool_start_time
                        logger.debug(
                            "Tool execution completed",
                            extra={
                                "tool_name": tool_name,
                                "duration_ms": int(tool_duration * 1000),
                            },
                        )

                        # Add tool call and response to messages
                        anthropic_messages.append(
                            self.schema_adapter.create_assistant_message(
                                f"I'll use the {tool_name} tool with input: "
                                f"{json.dumps(tool_params)}"
                            )
                        )
                        anthropic_messages.append(
                            self.schema_adapter.create_tool_response_message(
                                tool_name=tool_name, result=tool_response
                            )
                        )
                    except Exception as e:
                        tool_duration = time.time() - tool_start_time
                        logger.error(
                            "Tool execution failed",
                            extra={
                                "tool_name": tool_name,
                                "error": sanitize_log_message(str(e)),
                                "duration_ms": int(tool_duration * 1000),
                                "traceback": traceback.format_exc(),
                            },
                        )
                        anthropic_messages.append(
                            self.schema_adapter.create_tool_response_message(
                                tool_name=tool_name, error=str(e)
                            )
                        )

                # Continue the loop to handle more tool calls

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Error in Anthropic conversation",
                extra={
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                    "traceback": traceback.format_exc(),
                },
            )
            raise ValueError(f"Error in Anthropic conversation: {e!s}")
        finally:
            duration = time.time() - start_time
            logger.info(
                "Query processing completed",
                extra={"duration_ms": int(duration * 1000)},
            )
