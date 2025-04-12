"""Schema adapter for converting between MCP and OpenAI formats."""

import json
import logging
from typing import Any, ClassVar

from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


class SchemaAdapter:
    """Adapter for converting between MCP and OpenAI schemas."""

    # Fields that are not supported in OpenAI's function calling schema
    UNSUPPORTED_SCHEMA_FIELDS: ClassVar[set[str]] = {
        "title",
        "default",
        "$schema",
        "additionalProperties",
    }

    def clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Clean a JSON schema for OpenAI compatibility."""
        return self._clean_schema_internal(schema)

    def _clean_schema_internal(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Internal method for recursively cleaning schema."""
        if not isinstance(schema, dict):
            return schema

        cleaned = {}

        # Copy allowed fields
        for key in ["type", "properties", "required", "items", "enum", "description"]:
            if key in schema:
                cleaned[key] = schema[key]

        # Recursively clean nested properties
        if "properties" in cleaned:
            cleaned_props = {}
            for prop_name, prop_schema in cleaned["properties"].items():
                cleaned_props[prop_name] = self._clean_schema_internal(prop_schema)
            cleaned["properties"] = cleaned_props

        # Recursively clean array items
        if "items" in cleaned:
            cleaned["items"] = self._clean_schema_internal(cleaned["items"])

        return cleaned

    def convert_mcp_tool_to_openai(self, tool: MCPTool) -> dict[str, Any]:
        """Convert a single MCP tool to OpenAI format.

        Args:
            tool: MCP tool to convert

        Returns:
            Tool in OpenAI format
        """
        # Get and clean the schema
        schema = tool.inputSchema if hasattr(tool, "inputSchema") else {}
        cleaned_schema = self.clean_schema(schema)

        # Create OpenAI function format
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": cleaned_schema,
            },
        }

    def convert_mcp_tools_to_openai(self, tools: list[MCPTool]) -> list[dict[str, Any]]:
        """Convert multiple MCP tools to OpenAI format.

        Args:
            tools: List of MCP tools to convert

        Returns:
            List of tools in OpenAI format
        """
        return [self.convert_mcp_tool_to_openai(tool) for tool in tools]

    @staticmethod
    def create_user_message(query: str) -> dict[str, str]:
        """Create a user message in OpenAI format."""
        return {"role": "user", "content": query}

    @staticmethod
    def create_assistant_message(
        content: str | None = None, tool_calls: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Create an assistant message in OpenAI format."""
        message: dict[str, Any] = {"role": "assistant"}
        if content is not None:
            message["content"] = content
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        return message

    @staticmethod
    def create_tool_response_message(
        tool_call_id: str,
        result: CallToolResult | str | None = None,
        error: str | None = None,
    ) -> dict[str, str]:
        """Create a tool response message in OpenAI format."""
        content = str(error if error else result)
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }

    @staticmethod
    def extract_tool_calls(message: Any) -> list[tuple[str, dict[str, Any]]]:
        """Extract tool calls from an OpenAI message.

        Args:
            message: OpenAI message object

        Returns:
            List of tuples containing (tool_name, tool_args)
        """
        tool_calls = []

        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    tool_calls.append((tool_call.function.name, function_args))
                except json.JSONDecodeError:
                    logger.error(
                        "Failed to parse tool arguments",
                        extra={"tool_call": tool_call},
                    )

        return tool_calls
