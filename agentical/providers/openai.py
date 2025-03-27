"""OpenAI provider implementation."""

from typing import List, Dict, Any
import json
from openai import AsyncOpenAI

from agentical.core import Tool
from agentical.core import Provider, ProviderConfig, ProviderError
from agentical.core import ToolExecutor

class OpenAIProvider(Provider):
    """OpenAI provider implementation."""
    
    def __init__(self, config: ProviderConfig, executor: ToolExecutor):
        """Initialize OpenAI provider.
        
        Args:
            config: Provider configuration
            executor: Tool executor for handling tool calls
            
        Raises:
            ProviderError: If initialization fails
        """
        self.config = config
        self.executor = executor
        if not config.model:
            config.model = "gpt-4-turbo"
            
        try:
            self._client = AsyncOpenAI(api_key=config.api_key)
        except Exception as e:
            raise ProviderError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def get_name(self) -> str:
        """Get the name of the provider."""
        return "openai"
    
    def get_description(self) -> str:
        """Get a description of the provider."""
        return "OpenAI provider supporting GPT models with function calling capabilities"
    
    async def run_conversation(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Tool]
    ) -> str:
        """Run a conversation using OpenAI's chat completion API.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
            
        Returns:
            The model's response as a string
            
        Raises:
            ProviderError: If there's an error communicating with OpenAI
        """
        try:
            formatted_tools = self._format_tools(tools)
            
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=formatted_tools
            )
            
            message = response.choices[0].message
            
            # Check if the model wanted to call a function
            if message.tool_calls:
                # Extend conversation with function responses
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    function_response = await self.executor.execute_tool(
                        function_name, function_args
                    )
                    
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(function_response)
                    })
                
                # Get a new response from the model
                return await self.run_conversation(messages, tools)
            
            return message.content
            
        except Exception as e:
            raise ProviderError(f"Error in OpenAI conversation: {str(e)}")
    
    def _format_tools(self, tools: List[Tool]) -> List[Dict[str, Any]]:
        """Format tools for OpenAI's function calling format."""
        formatted_tools = []
        for tool in tools:
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            for param in tool.parameters:
                formatted_tool["function"]["parameters"]["properties"][param] = {
                    "type": tool.parameters[param].type,
                    "description": tool.parameters[param].description
                }
                if tool.parameters[param].required:
                    formatted_tool["function"]["parameters"]["required"].append(param)
                if tool.parameters[param].enum:
                    formatted_tool["function"]["parameters"]["properties"][param]["enum"] = tool.parameters[param].enum
            
            formatted_tools.append(formatted_tool)
        
        return formatted_tools 