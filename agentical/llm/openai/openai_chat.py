"""OpenAI implementation for chat interactions."""

import logging
import os
import time
from collections.abc import Callable
from typing import Any

import openai
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool
from mcp.types import Prompt as MCPPrompt
from mcp.types import Resource as MCPResource

from agentical.api.llm_backend import LLMBackend
from agentical.utils.log_utils import sanitize_log_message

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)


class OpenAIBackend(LLMBackend[list[dict[str, str]]]):
    """OpenAI implementation for chat interactions."""

    DEFAULT_MODEL = "gpt-4-turbo-preview"

    def __init__(self, api_key: str | None = None):
        """Initialize the OpenAI backend.

        Args:
            api_key: Optional OpenAI API key. If not provided, will look for
                OPENAI_API_KEY env var.

        Raises:
            ValueError: If API key is not provided or found in environment

        Environment Variables:
            OPENAI_API_KEY: API key for OpenAI
            OPENAI_MODEL: Model to use (defaults to DEFAULT_MODEL if not set)
        """
        logger.info("Initializing OpenAI backend")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found")
            raise ValueError(
                "OPENAI_API_KEY not found. Please provide it or set in environment."
            )

        try:
            self.client = openai.AsyncOpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL)
            self.schema_adapter = SchemaAdapter()
            logger.info(
                "Initialized OpenAI client",
                extra={"model": self.model, "api_key_length": len(api_key)},
            )
        except Exception as e:
            error_msg = sanitize_log_message(
                f"Failed to initialize OpenAI client: {e!s}"
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def convert_tools(self, tools: list[MCPTool]) -> list[dict[str, Any]]:
        """Format tools for OpenAI's function calling format.

        Args:
            tools: List of MCP tools to convert

        Returns:
            List of tools in OpenAI function format
        """
        start_time = time.time()
        try:
            formatted_tools = self.schema_adapter.convert_mcp_tools_to_openai(tools)
            duration = time.time() - start_time
            logger.debug(
                "Tool formatting completed",
                extra={"num_tools": len(tools), "duration_ms": int(duration * 1000)},
            )
            return formatted_tools
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Tool formatting failed",
                extra={"error": str(e), "duration_ms": int(duration * 1000)},
            )
            raise

    async def process_query(
        self,
        query: str,
        tools: list[MCPTool],
        resources: list[MCPResource],
        prompts: list[MCPPrompt],
        execute_tool: Callable[[str, dict[str, Any]], CallToolResult],
        context: list[dict[str, str]] | None = None,
    ) -> str:
        """Process a query using OpenAI with the given tools.

        Args:
            query: The user's query
            tools: List of available MCP tools
            resources: List of available MCP resources
            prompts: List of available MCP prompts
            execute_tool: Function to execute a tool call
            context: Optional conversation context

        Returns:
            Generated response from OpenAI

        Raises:
            ValueError: If there's an error communicating with OpenAI
        """
        start_time = time.time()
        try:
            logger.info(
                "Processing query",
                extra={
                    "query": query,
                    "num_tools": len(tools),
                    "num_resources": len(resources),
                    "num_prompts": len(prompts),
                    "has_context": context is not None,
                },
            )

            # Initialize or use existing conversation context
            messages = list(context) if context else []
            messages.append(self.schema_adapter.create_user_message(query))

            # Convert tools to OpenAI format
            formatted_tools = self.convert_tools(tools)

            while True:  # Continue until we get a response without tool calls
                # Get response from OpenAI
                api_start = time.time()
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=formatted_tools,
                    tool_choice="auto",
                )
                api_duration = time.time() - api_start
                logger.debug(
                    "OpenAI API call completed",
                    extra={"duration_ms": int(api_duration * 1000)},
                )

                message = response.choices[0].message

                # Extract tool calls
                tool_calls = self.schema_adapter.extract_tool_calls(message)

                # If no tool calls and we have content, return the final response
                if not tool_calls and message.content:
                    duration = time.time() - start_time
                    logger.info(
                        "Query completed without tool calls",
                        extra={"duration_ms": int(duration * 1000)},
                    )
                    return message.content

                # If no tool calls and no content, continue the conversation
                if not tool_calls:
                    messages.append(
                        self.schema_adapter.create_assistant_message(
                            content="I encountered an error. Let me try again."
                        )
                    )
                    continue

                # Add assistant message with tool calls
                messages.append(
                    self.schema_adapter.create_assistant_message(
                        content=None,
                        tool_calls=[
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                            for tool_call in message.tool_calls
                        ],
                    )
                )

                # Handle each tool call
                for tool_call, (function_name, function_args) in zip(
                    message.tool_calls, tool_calls
                ):
                    # Execute the tool
                    tool_start = time.time()
                    try:
                        function_response = await execute_tool(
                            function_name, function_args
                        )
                        tool_duration = time.time() - tool_start
                        logger.debug(
                            "Tool execution completed",
                            extra={
                                "tool_name": function_name,
                                "duration_ms": int(tool_duration * 1000),
                            },
                        )
                    except Exception as e:
                        tool_duration = time.time() - tool_start
                        logger.error(
                            "Tool execution failed",
                            extra={
                                "tool_name": function_name,
                                "error": sanitize_log_message(str(e)),
                                "duration_ms": int(tool_duration * 1000),
                            },
                        )
                        function_response = f"Error: {e!s}"

                    # Add tool response to conversation
                    messages.append(
                        self.schema_adapter.create_tool_response_message(
                            tool_call_id=tool_call.id,
                            result=function_response,
                        )
                    )

                # Continue the loop to let the model make more tool calls

        except Exception as e:
            duration = time.time() - start_time
            error_msg = sanitize_log_message(f"Error in OpenAI conversation: {e!s}")
            logger.error(
                error_msg,
                extra={"error": str(e), "duration_ms": int(duration * 1000)},
                exc_info=True,
            )
            raise ValueError(error_msg)
        finally:
            duration = time.time() - start_time
            logger.info(
                "Query processing completed",
                extra={"duration_ms": int(duration * 1000)},
            )
