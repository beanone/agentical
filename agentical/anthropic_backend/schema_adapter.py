"""Schema adapter for converting between MCP and Anthropic formats."""

import json
import logging
import re
from typing import Any, Dict, List, Set, Tuple

from anthropic.types import Message, MessageParam

from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)

class SchemaAdapter:
    """Adapter for converting between MCP and Anthropic schemas."""
    
    # Fields that are not supported in Anthropic's function calling schema
    UNSUPPORTED_SCHEMA_FIELDS: Set[str] = {
        "title",
        "default",
        "$schema",
        "additionalProperties"
    }

    @staticmethod
    def extract_answer(text: str) -> str:
        """Extract the content within <answer> tags, or return the full text if not found.
        
        Args:
            text: The text to extract answer from
            
        Returns:
            The extracted answer or original text if no answer tags found
        """
        match = re.search(r'<answer>(.*?)</answer>', text, re.DOTALL)
        return match.group(1).strip() if match else text
    
    def convert_mcp_tools_to_anthropic(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Anthropic format."""
        logger.debug("TEST LOG - Starting tool conversion")
        logger.debug(f"Converting {len(tools)} MCP tools to Anthropic format")
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
                    "required": []
                }
            }
            
            # Get and clean the schema from the tool's parameters
            if hasattr(tool, 'parameters'):
                schema = self.clean_schema(tool.parameters)
                logger.debug(f"Cleaned schema for {tool.name}: {json.dumps(schema, indent=2)}")
                
                # Copy over properties and required fields
                if "properties" in schema:
                    formatted_tool["input_schema"]["properties"] = schema["properties"]
                if "required" in schema:
                    formatted_tool["input_schema"]["required"] = schema["required"]
            
            logger.debug(f"Formatted tool result: {json.dumps(formatted_tool, indent=2)}")
            formatted_tools.append(formatted_tool)
        
        logger.debug(f"Converted {len(formatted_tools)} tools successfully")
        return formatted_tools
    
    def clean_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean a JSON schema for Anthropic compatibility."""
        return self._clean_schema_internal(schema)
    
    def _clean_schema_internal(self, schema: Dict[str, Any]) -> Dict[str, Any]:
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
        msg = {
            "role": "user",
            "content": [{"type": "text", "text": query}]
        }
        logger.debug(f"Created user message: {json.dumps(msg, indent=2)}")
        return msg

    @staticmethod
    def create_system_message(content: str) -> List[Dict[str, str]]:
        """Create a system message in Anthropic format."""
        msg = [{"type": "text", "text": content}]
        logger.debug(f"Created system message: {json.dumps(msg, indent=2)}")
        return msg

    @staticmethod
    def create_assistant_message(content: str) -> MessageParam:
        """Create an assistant message in Anthropic format."""
        msg = {
            "role": "assistant",
            "content": [{"type": "text", "text": content}]
        }
        logger.debug(f"Created assistant message: {json.dumps(msg, indent=2)}")
        return msg

    @staticmethod
    def create_tool_response_message(tool_name: str, result: Any = None, error: str = None) -> MessageParam:
        """Create a tool response message in Anthropic format."""
        content = f"Tool {tool_name} returned: {str(result)}" if result else f"Tool {tool_name} error: {error}"
        msg = {
            "role": "user",
            "content": [{"type": "text", "text": content}]
        }
        logger.debug(f"Created tool response message: {json.dumps(msg, indent=2)}")
        return msg

    @staticmethod
    def extract_tool_calls(response: Message) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract tool calls from an Anthropic message."""
        tool_calls = []
        
        if hasattr(response, 'content'):
            logger.debug(f"Processing response content blocks: {len(response.content)} blocks")
            for block in response.content:
                logger.debug(f"Processing content block type: {block.type}")
                if block.type == "tool_use":
                    logger.debug(f"Found tool_use block: {json.dumps(block.dict(), indent=2)}")
                    tool_calls.append((
                        block.name,
                        block.input
                    ))
        
        logger.debug(f"Extracted {len(tool_calls)} tool calls")
        return tool_calls 