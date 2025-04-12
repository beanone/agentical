"""Schema adapter for converting between MCP and Anthropic formats."""

import logging
import re
from typing import Any, ClassVar

from anthropic.types import Message, MessageParam
from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


class SchemaAdapter:
    """Adapter for converting between MCP and Anthropic schemas."""

    # Fields that are not supported in Anthropic's function calling schema
    UNSUPPORTED_SCHEMA_FIELDS: ClassVar[set[str]] = {
        "title",
        "default",
        "$schema",
        "additionalProperties",
    }

    @staticmethod
    def extract_answer(text: str) -> str:
        """Extract the content within <answer> tags, or return the full text if not
        found.

        Args:
            text: The text to extract answer from

        Returns:
            The extracted answer or original text if no answer tags found
        """
        match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)
        return match.group(1).strip() if match else text

    def convert_mcp_tools_to_anthropic(
        self, tools: list[MCPTool]
    ) -> list[dict[str, Any]]:
        """Convert MCP tools to Anthropic format."""
        logger.debug(
            "Converting MCP tools to Anthropic format", extra={"num_tools": len(tools)}
        )
        formatted_tools = []

        for tool in tools:
            # Create Anthropic tool format - matching reference implementation exactly
            formatted_tool = {
                "type": "custom",
                "name": tool.name,
                "description": tool.description,  # description at top level
                "input_schema": {  # input_schema at top level
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }

            # Get and clean the schema from the tool's parameters
            if hasattr(tool, "parameters"):
                schema = self.clean_schema(tool.parameters)
                logger.debug(
                    "Cleaned tool schema",
                    extra={"tool_name": tool.name, "schema": schema},
                )

                # Copy over properties and required fields
                if "properties" in schema:
                    formatted_tool["input_schema"]["properties"] = schema["properties"]
                if "required" in schema:
                    formatted_tool["input_schema"]["required"] = schema["required"]

            formatted_tools.append(formatted_tool)

        logger.debug(
            "Tool conversion completed", extra={"num_tools": len(formatted_tools)}
        )
        return formatted_tools

    def clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Clean a JSON schema for Anthropic compatibility."""
        return self._clean_schema_internal(schema)

    def _clean_schema_internal(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Internal method for recursively cleaning schema."""
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

    @staticmethod
    def create_user_message(query: str) -> MessageParam:
        """Create a user message in Anthropic format."""
        return {"role": "user", "content": [{"type": "text", "text": query}]}

    @staticmethod
    def create_system_message(content: str) -> list[dict[str, str]]:
        """Create a system message in Anthropic format."""
        return [{"type": "text", "text": content}]

    @staticmethod
    def create_assistant_message(content: str) -> MessageParam:
        """Create an assistant message in Anthropic format."""
        return {"role": "assistant", "content": [{"type": "text", "text": content}]}

    @staticmethod
    def create_tool_response_message(
        tool_name: str, result: Any | None = None, error: str | None = None
    ) -> MessageParam:
        """Create a tool response message in Anthropic format."""
        content = (
            f"Tool {tool_name} returned: {result!s}"
            if result
            else f"Tool {tool_name} error: {error}"
        )
        return {"role": "user", "content": [{"type": "text", "text": content}]}

    @staticmethod
    def extract_tool_calls(response: Message) -> list[tuple[str, dict[str, Any]]]:
        """Extract tool calls from an Anthropic message."""
        tool_calls = []

        if hasattr(response, "content"):
            logger.debug(
                "Processing response content",
                extra={"num_blocks": len(response.content)},
            )
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append((block.name, block.input))

        return tool_calls
