"""Gemini implementation for chat interactions."""

import logging
import os
from typing import Any, Dict, List, Optional, Callable

from google import genai
from google.genai.types import Content

from agentical.api.llm_backend import LLMBackend
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

from .schema_adapter import SchemaAdapter

logger = logging.getLogger(__name__)

class GeminiBackend(LLMBackend):
    """Gemini implementation for chat interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini backend.
        
        Args:
            api_key: Optional Gemini API key. If not provided, will look for GEMINI_API_KEY env var.
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please provide it or set in environment.")
            
        self.client = genai.Client(api_key=api_key)
        self.model = SchemaAdapter.DEFAULT_MODEL
        self.schema_adapter = SchemaAdapter()

    def convert_tools(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Gemini format.
        
        Args:
            tools: List of MCP tools to convert
            
        Returns:
            List of tools in Gemini format
        """
        return self.schema_adapter.convert_mcp_tools_to_gemini(tools)

    async def process_query(
        self,
        query: str,
        tools: List[MCPTool],
        execute_tool: Callable[[str, Dict[str, Any]], CallToolResult],
        context: Optional[List[Content]] = None
    ) -> str:
        """Process a query using Gemini with the given tools.
        
        Args:
            query: The user's query
            tools: List of available MCP tools
            execute_tool: Function to execute a tool call
            context: Optional conversation context
            
        Returns:
            Generated response from Gemini
        """
        # Convert query to Gemini format and prepare contents
        contents = context or []
        contents.append(self.schema_adapter.create_user_content(query))
        
        # Convert tools to Gemini format
        gemini_tools = self.schema_adapter.convert_mcp_tools_to_gemini(tools)
        
        # Get initial response from Gemini
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                tools=gemini_tools,
            ),
        )
        
        final_text = []
        
        # Process response and handle tool calls
        for candidate in response.candidates:
            if candidate.content.parts:
                for part in candidate.content.parts:
                    tool_call = self.schema_adapter.extract_tool_call(part)
                    if tool_call:
                        tool_name, tool_args = tool_call
                        print(f"\n[Gemini requested tool call: {tool_name} with args {tool_args}]")
                        
                        # Execute the tool
                        try:
                            result = await execute_tool(tool_name, tool_args)
                            # Add tool response to context
                            contents.extend(
                                self.schema_adapter.create_tool_response_content(
                                    function_call_part=part,
                                    tool_name=tool_name,
                                    result=result
                                )
                            )
                        except Exception as e:
                            logger.error("Tool execution failed: %s", str(e))
                            contents.extend(
                                self.schema_adapter.create_tool_response_content(
                                    function_call_part=part,
                                    tool_name=tool_name,
                                    error=str(e)
                                )
                            )
                        
                        # Get final response from Gemini
                        response = self.client.models.generate_content(
                            model=self.model,
                            contents=contents,
                            config=genai.types.GenerateContentConfig(
                                tools=gemini_tools,
                            ),
                        )
                        
                        # Extract final response text
                        if response.candidates and response.candidates[0].content.parts:
                            final_text.append(response.candidates[0].content.parts[0].text)
                    elif hasattr(part, 'text'):
                        final_text.append(part.text)
        
        return "\n".join(final_text) if final_text else "No response generated" 