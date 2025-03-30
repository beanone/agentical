"""Schema adapter for converting between MCP and Gemini schemas."""

from typing import Any, Dict, List, Set, Optional

from google import genai
from google.genai.types import Tool as GeminiTool
from google.genai.types import FunctionDeclaration, Content, Part
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

class SchemaAdapter:
    """Adapter for converting between MCP and Gemini schemas."""
    
    # Fields that are not supported in Gemini's function calling schema
    UNSUPPORTED_SCHEMA_FIELDS: Set[str] = {
        "title",
        "default",
        "$schema",
        "additionalProperties"
    }

    # Default model to use for Gemini API
    DEFAULT_MODEL: str = "gemini-2.0-flash-001"

    @staticmethod
    def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively removes unsupported fields from the JSON schema.
        
        Args:
            schema: The schema dictionary
            
        Returns:
            Cleaned schema without unsupported fields
        """
        if not isinstance(schema, dict):
            return schema
            
        # Create a new dict to avoid modifying the input
        cleaned = {}
        
        # First pass: collect all properties
        for key, value in schema.items():
            # Skip unsupported fields unless they're required properties
            if key in SchemaAdapter.UNSUPPORTED_SCHEMA_FIELDS and key != "required":
                continue
                
            # Recursively clean nested objects
            if isinstance(value, dict):
                cleaned[key] = SchemaAdapter.clean_schema(value)
            # Handle arrays with item definitions
            elif key == "items" and isinstance(value, dict):
                cleaned[key] = SchemaAdapter.clean_schema(value)
            # Handle arrays of schemas
            elif isinstance(value, list):
                cleaned[key] = [
                    SchemaAdapter.clean_schema(item) if isinstance(item, dict) else item 
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
            
            # Add non-optional string properties that exist
            for prop_name, prop_schema in properties.items():
                if (isinstance(prop_schema, dict) and 
                    prop_schema.get("type") == "string" and 
                    "optional" not in prop_schema and
                    prop_name not in required_props):
                    required_props.append(prop_name)
            
            if required_props:
                cleaned["required"] = required_props
                
        return cleaned
    
    @staticmethod
    def convert_mcp_tool_to_gemini(tool: MCPTool) -> GeminiTool:
        """Convert a single MCP tool to Gemini Tool type.
        
        Args:
            tool: MCP tool to convert
            
        Returns:
            Converted Gemini Tool
        """
        # Clean the schema but preserve its structure
        parameters = SchemaAdapter.clean_schema(tool.inputSchema)
        
        # Handle empty object properties
        if not parameters.get("properties"):
            parameters["properties"] = {
                "random_string": {
                    "type": "string",
                    "description": "Dummy parameter for no-parameter tools"
                }
            }
        
        # Create function declaration
        function_declaration = FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=parameters
        )
        
        # Wrap in a Tool object
        return GeminiTool(function_declarations=[function_declaration])
    
    @staticmethod
    def convert_mcp_tools_to_gemini(tools: List[MCPTool]) -> List[GeminiTool]:
        """Convert multiple MCP tools to Gemini Tool types.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of converted Gemini Tools
        """
        return [SchemaAdapter.convert_mcp_tool_to_gemini(tool) for tool in tools]

    @staticmethod
    def create_user_content(query: str) -> Content:
        """Create Gemini content from user query.
        
        Args:
            query: User's query text
            
        Returns:
            Gemini Content object
        """
        return Content(
            role='user',
            parts=[Part.from_text(text=query)]
        )

    @staticmethod
    def create_tool_response_content(
        function_call_part: Part,
        tool_name: str,
        result: Optional[CallToolResult] = None,
        error: Optional[str] = None
    ) -> List[Content]:
        """Create Gemini content for tool response.
        
        Args:
            function_call_part: The function call part from Gemini
            tool_name: Name of the tool called
            result: Optional successful result from tool execution
            error: Optional error message if tool execution failed
            
        Returns:
            List of Gemini Content objects
        """
        if error:
            response_dict = {"error": error}
        else:
            # Handle list responses by wrapping them in a dictionary
            content = result.content
            if isinstance(content, list):
                response_dict = {"items": content}
            else:
                response_dict = {"result": content}
        
        return [
            Content(role='assistant', parts=[function_call_part]),
            Content(role='tool', parts=[Part.from_function_response(
                name=tool_name,
                response=response_dict
            )])
        ]

    @staticmethod
    def extract_tool_call(part: Part) -> Optional[tuple[str, Dict[str, Any]]]:
        """Extract tool call details from a Gemini response part.
        
        Args:
            part: Gemini response part
            
        Returns:
            Tuple of (tool_name, tool_args) if part contains a function call,
            None otherwise
        """
        if part.function_call:
            return (part.function_call.name, part.function_call.args)
        return None 