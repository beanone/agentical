"""Anthropic provider implementation."""

from typing import List, Dict, Any
from anthropic import AsyncAnthropic

from agentical.core import Tool
from agentical.core import Provider, ProviderConfig, ProviderError
from agentical.core import ToolExecutor
import traceback

# Default max tokens for responses
DEFAULT_MAX_TOKENS = 4096

class AnthropicProvider(Provider):
    """Anthropic provider implementation."""
    
    def __init__(self, config: ProviderConfig, executor: ToolExecutor):
        """Initialize Anthropic provider.
        
        Args:
            config: Provider configuration
            executor: Tool executor for handling tool calls
            
        Raises:
            ProviderError: If initialization fails
        """
        self.config = config
        self.executor = executor
            
        try:
            self._client = AsyncAnthropic(api_key=config.api_key)
        except Exception as e:
            raise ProviderError(f"Failed to initialize Anthropic client: {str(e)}")
    
    def get_name(self) -> str:
        """Get the name of the provider."""
        return "anthropic"
    
    def get_description(self) -> str:
        """Get a description of the provider."""
        return "Anthropic provider supporting Claude models with function calling capabilities"
    
    async def run_conversation(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Tool]
    ) -> str:
        """Run a conversation using Anthropic's chat API.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
            
        Returns:
            The model's response as a string
            
        Raises:
            ProviderError: If there's an error communicating with Anthropic
        """
        try:
            formatted_tools = self._format_tools(tools)
            
            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None
            for msg in messages:
                if msg["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg["content"]})
                elif msg["role"] == "system":
                    # System message is handled differently in Anthropic
                    system_message = msg["content"]
            
            response = await self._client.messages.create(
                model=self.config.model,
                system=system_message,
                messages=anthropic_messages,
                tools=formatted_tools,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            
            # Extract content blocks
            content_blocks = response.content
            
            # Combine text blocks and handle tool use blocks
            result_text = []
            for block in content_blocks:
                if block.type == 'text':
                    result_text.append(block.text)
                elif block.type == 'tool_use':
                    # Execute the tool
                    tool_output = await self.executor.execute_tool(
                        block.name, block.input
                    )
                    
                    # Add the tool call and output to the messages
                    anthropic_messages.append({
                        "role": "assistant", 
                        "content": f"I'll use the {block.name} tool with input: {block.input}"
                    })
                    anthropic_messages.append({
                        "role": "user",
                        "content": f"Tool {block.name} returned: {str(tool_output)}"
                    })
                    
                    # Get a new response with the tool result
                    return await self.run_conversation(
                        [{"role": "system", "content": system_message}] + anthropic_messages, 
                        tools
                    )
            
            return " ".join(result_text)
            
        except Exception as e:
            traceback.print_exc()
            raise ProviderError(f"Error in Anthropic conversation: {str(e)}")
    
    def _format_tools(self, tools: List[Tool]) -> List[Dict[str, Any]]:
        """Format tools for Anthropic's function calling format."""
        formatted_tools = []
        for tool in tools:
            formatted_tool = {
                "type": "custom",
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            for param_name, param in tool.parameters.items():
                formatted_tool["input_schema"]["properties"][param_name] = {
                    "type": param.type,
                    "description": param.description
                }
                if param.required:
                    formatted_tool["input_schema"]["required"].append(param_name)
                if param.enum:
                    formatted_tool["input_schema"]["properties"][param_name]["enum"] = param.enum
            
            formatted_tools.append(formatted_tool)
        
        return formatted_tools 