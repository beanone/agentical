"""LLM Integration for Agentical Framework.

This module provides integration with LLM providers for tool execution.
"""

import json
from typing import Dict, List, Any, Optional, Union, Literal

from agentical.core.registry import ToolRegistry
from agentical.core.executor import ToolExecutor


class LLMToolIntegration:
    """Integration between LLM and tools.
    
    This class provides the integration layer between LLMs (like OpenAI's GPT or 
    Anthropic's Claude) and the tool execution framework.
    """
    
    def __init__(
        self, 
        registry: ToolRegistry, 
        executor: ToolExecutor,
        model_provider: Literal["openai", "anthropic"] = "openai",
        client: Optional[Any] = None
    ) -> None:
        """Initialize LLM tool integration.
        
        Args:
            registry: The tool registry containing available tools
            executor: The tool executor for handling tool calls
            model_provider: The LLM provider to use
            client: Optional pre-configured client (useful for testing)
        """
        self.registry = registry
        self.executor = executor
        self.model_provider = model_provider
        
        # Use provided client or initialize a new one
        if client is not None:
            self.client = client
        else:
            # Initialize the appropriate client based on the model provider
            if model_provider == "openai":
                # Lazy import to avoid requiring OpenAI if not used
                try:
                    from openai import AsyncOpenAI
                    self.client = AsyncOpenAI()
                except ImportError:
                    self.client = None
                    print("Warning: OpenAI package not installed. Please install with 'pip install openai'")
            elif model_provider == "anthropic":
                # Lazy import to avoid requiring Anthropic if not used
                try:
                    from anthropic import AsyncAnthropic
                    self.client = AsyncAnthropic()
                except ImportError:
                    self.client = None
                    print("Warning: Anthropic package not installed. Please install with 'pip install anthropic'")
            else:
                raise ValueError(f"Unsupported model provider: {model_provider}")
    
    async def run_conversation(
        self, 
        messages: List[Dict[str, Any]], 
        model: Optional[str] = None
    ) -> str:
        """Run a conversation with tools.
        
        Args:
            messages: The conversation history
            model: The specific model to use (defaults to a reasonable model for the provider)
            
        Returns:
            The LLM's response
            
        Raises:
            ValueError: If client is not initialized or model provider is not supported
        """
        if self.client is None:
            raise ValueError(f"Client for {self.model_provider} is not initialized")
        
        if self.model_provider == "openai":
            return await self._run_openai_conversation(messages, model or "gpt-4-turbo")
        elif self.model_provider == "anthropic":
            return await self._run_anthropic_conversation(messages, model or "claude-3-sonnet-20240229")
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
    
    async def _run_openai_conversation(self, messages: List[Dict[str, Any]], model: str) -> str:
        """Run a conversation with OpenAI.
        
        Args:
            messages: The conversation history
            model: The OpenAI model to use
            
        Returns:
            The model's response
        """
        tools = self.registry.to_openai_format()
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
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
            return await self._run_openai_conversation(messages, model)
        
        return message.content
    
    async def _run_anthropic_conversation(self, messages: List[Dict[str, Any]], model: str) -> str:
        """Run a conversation with Anthropic.
        
        Args:
            messages: The conversation history
            model: The Anthropic model to use
            
        Returns:
            The model's response
        """
        tools = self.registry.to_anthropic_format()
        
        # Convert messages to Anthropic format if needed
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
        
        response = await self.client.messages.create(
            model=model,
            system=system_message,
            messages=anthropic_messages,
            tools=tools
        )
        
        # Extract the text content from the response
        content = response.content[0].text
        
        # Check if the model wanted to call a tool
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                
                tool_output = await self.executor.execute_tool(
                    tool_name, tool_input
                )
                
                # Add the tool call and output to the messages
                anthropic_messages.append({
                    "role": "assistant", 
                    "content": "",
                    "tool_calls": [{
                        "id": tool_call.id,
                        "name": tool_name, 
                        "input": tool_input
                    }]
                })
                anthropic_messages.append({
                    "role": "user",
                    "content": "",
                    "tool_results": [{
                        "tool_call_id": tool_call.id,
                        "content": str(tool_output)
                    }]
                })
            
            # Get a new response from the model
            return await self._run_anthropic_conversation(
                [{"role": "system", "content": system_message}] + anthropic_messages, 
                model
            )
        
        return content 