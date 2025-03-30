"""Schema adapter for converting between MCP and Anthropic schemas."""

import json
import logging
from typing import Any, Dict, List, Set

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

    # Default model to use for Anthropic API
    DEFAULT_MODEL: str = "claude-3-opus-20240229"

    @staticmethod
    def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively removes unsupported fields from the JSON schema."""
        logger.debug(f"Cleaning schema: {json.dumps(schema, indent=2)}")
        cleaned = SchemaAdapter._clean_schema_internal(schema)
        logger.debug(f"Cleaned schema result: {json.dumps(cleaned, indent=2)}")
        return cleaned

    @staticmethod
    def _clean_schema_internal(schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(schema, dict):
            return schema
            
        cleaned = {}
        
        # First pass: collect all properties
        for key, value in schema.items():
            # Skip unsupported fields unless they're required properties
            if key in SchemaAdapter.UNSUPPORTED_SCHEMA_FIELDS and key != "required":
                logger.debug(f"Skipping unsupported field: {key}")
                continue
                
            # Recursively clean nested objects
            if isinstance(value, dict):
                cleaned[key] = SchemaAdapter._clean_schema_internal(value)
            # Handle arrays with item definitions
            elif key == "items" and isinstance(value, dict):
                cleaned[key] = SchemaAdapter._clean_schema_internal(value)
            # Handle arrays of schemas
            elif isinstance(value, list):
                cleaned[key] = [
                    SchemaAdapter._clean_schema_internal(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                cleaned[key] = value

        # Second pass: validate required properties exist in properties
        if "properties" in cleaned:
            properties = cleaned.get("properties", {})
            required_props = []
            
            # Get required properties from schema
            schema_required = cleaned.get("required", [])
            
            # Add properties that are required and exist
            for prop_name in schema_required:
                if prop_name in properties:
                    required_props.append(prop_name)
                else:
                    logger.warning(f"Required property '{prop_name}' not found in properties")
            
            if required_props:
                cleaned["required"] = required_props
                logger.debug(f"Final required properties: {required_props}")
                
        return cleaned


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
    def extract_tool_calls(response: Message) -> List[tuple[str, Dict[str, Any]]]:
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
                        block.parameters
                    ))
        
        logger.debug(f"Extracted {len(tool_calls)} tool calls")
        return tool_calls 