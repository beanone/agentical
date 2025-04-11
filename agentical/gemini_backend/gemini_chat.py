"""Gemini implementation for chat interactions."""

import logging
import os
import time
from collections.abc import Callable
from typing import Any

from google import genai
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool
from mcp.types import Prompt as MCPPrompt
from mcp.types import Resource as MCPResource

from agentical.api.llm_backend import LLMBackend
from agentical.utils.log_utils import sanitize_log_message

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)


class GeminiBackend(LLMBackend[list[dict[str, Any]]]):
    """Gemini implementation for chat interactions."""

    DEFAULT_MODEL = "gemini-2.0-flash-001"

    def __init__(self, api_key: str | None = None):
        """Initialize the Gemini backend.

        Args:
            api_key: Optional Gemini API key. If not provided, will look for
                GEMINI_API_KEY env var.

        Environment Variables:
            GEMINI_API_KEY: API key for Gemini
            GEMINI_MODEL: Model to use (defaults to DEFAULT_MODEL if not set)
        """
        logger.info("Initializing Gemini backend")
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please provide it or set in environment."
            )

        try:
            self.client = genai.Client(api_key=api_key)
            self.model = os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
            self.schema_adapter = SchemaAdapter()
            logger.info(
                "Initialized Gemini client",
                extra={"model": self.model, "api_key_length": len(api_key)},
            )
        except Exception as e:
            error_msg = sanitize_log_message(
                f"Failed to initialize Gemini client: {e!s}"
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def convert_tools(self, tools: list[MCPTool]) -> list[dict[str, Any]]:
        """Convert MCP tools to Gemini format.

        Args:
            tools: List of MCP tools to convert

        Returns:
            List of tools in Gemini format
        """
        start_time = time.time()
        try:
            result = self.schema_adapter.convert_mcp_tools_to_gemini(tools)
            duration = time.time() - start_time
            logger.debug(
                "Tool conversion completed",
                extra={"num_tools": len(tools), "duration_ms": int(duration * 1000)},
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Tool conversion failed",
                extra={"error": str(e), "duration_ms": int(duration * 1000)},
            )
            raise

    def convert_prompts(self, prompts: list[MCPPrompt]) -> list[dict[str, Any]]:
        """Convert MCP prompts to Gemini format.

        Args:
            prompts: List of MCP prompts to convert

        Returns:
            List of prompts in Gemini format
        """
        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "content": prompt.content,
            }
            for prompt in prompts
        ]

    def convert_resources(self, resources: list[MCPResource]) -> list[dict[str, Any]]:
        """Convert MCP resources to Gemini format.

        Args:
            resources: List of MCP resources to convert

        Returns:
            List of resources in Gemini format
        """
        return [
            {
                "name": resource.name,
                "description": resource.description,
                "uri": resource.uri,
                "mimeType": resource.mimeType,
                "size": resource.size,
                "annotations": resource.annotations,
            }
            for resource in resources
        ]

    async def process_query(
        self,
        query: str,
        tools: list[MCPTool],
        resources: list[MCPResource],
        prompts: list[MCPPrompt],
        execute_tool: Callable[[str, dict[str, Any]], CallToolResult],
        context: list[dict[str, Any]] | None = None,
    ) -> str:
        """Process a query using Gemini with the given tools.

        Args:
            query: The user's query
            tools: List of available MCP tools
            resources: List of available MCP resources
            prompts: List of available MCP prompts
            execute_tool: Function to execute a tool call
            context: Optional conversation context

        Returns:
            Generated response from Gemini
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
            # Convert query to Gemini format and prepare contents
            contents = context or []
            contents.append(self.schema_adapter.create_user_content(query))

            # Convert tools to Gemini format
            gemini_tools = self.schema_adapter.convert_mcp_tools_to_gemini(tools)

            while True:  # Continue until we get a response without tool calls
                # Get response from Gemini
                api_start = time.time()
                response = await self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        tools=gemini_tools,
                    ),
                )
                api_duration = time.time() - api_start
                logger.debug(
                    "Gemini API call completed",
                    extra={"duration_ms": int(api_duration * 1000)},
                )

                if not response.candidates:
                    logger.warning("No response candidates generated")
                    return "No response generated"

                has_tool_calls = False
                final_text = []

                # Process each candidate's content parts
                for candidate in response.candidates:
                    if not candidate.content.parts:
                        continue

                    for part in candidate.content.parts:
                        tool_call = self.schema_adapter.extract_tool_call(part)
                        if tool_call:
                            has_tool_calls = True
                            tool_name, tool_args = tool_call

                            # Execute the tool
                            tool_start = time.time()
                            try:
                                result = await execute_tool(tool_name, tool_args)
                                tool_duration = time.time() - tool_start
                                logger.debug(
                                    "Tool execution completed",
                                    extra={
                                        "tool_name": tool_name,
                                        "duration_ms": int(tool_duration * 1000),
                                    },
                                )
                                # Add tool response to context
                                contents.extend(
                                    self.schema_adapter.create_tool_response_content(
                                        function_call_part=part,
                                        tool_name=tool_name,
                                        result=result,
                                    )
                                )
                            except Exception as e:
                                tool_duration = time.time() - tool_start
                                logger.error(
                                    "Tool execution failed",
                                    extra={
                                        "tool_name": tool_name,
                                        "error": sanitize_log_message(str(e)),
                                        "duration_ms": int(tool_duration * 1000),
                                    },
                                )
                                # Add error response to context
                                contents.extend(
                                    self.schema_adapter.create_tool_response_content(
                                        function_call_part=part,
                                        tool_name=tool_name,
                                        error=str(e),
                                    )
                                )
                        else:
                            final_text.append(part.text)

                # If no tool calls, return the final response
                if not has_tool_calls:
                    duration = time.time() - start_time
                    logger.info(
                        "Query completed without tool calls",
                        extra={"duration_ms": int(duration * 1000)},
                    )
                    return " ".join(final_text) or "No response generated"

                # Continue the loop to handle more tool calls

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Error in Gemini conversation",
                extra={
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise ValueError(f"Error in Gemini conversation: {e!s}")
        finally:
            duration = time.time() - start_time
            logger.info(
                "Query processing completed",
                extra={"duration_ms": int(duration * 1000)},
            )
