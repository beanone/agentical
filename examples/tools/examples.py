"""Example using the weather, calculator, and filesystem tools with Agentical framework.

This script demonstrates how to use the OpenWeatherMap-based weather tool,
a simple calculator tool, and a filesystem tool with the Agentical framework.
It supports both OpenAI's GPT and Anthropic's Claude models.
"""

# Standard library imports
import asyncio
import os
from typing import Dict, Any, List, Optional

# Local imports
from agentical.core.registry import ToolRegistry
from agentical.core.executor import ToolExecutor
from agentical.providers.llm import LLMToolIntegration
from .weather_tool import (
    create_weather_tool, 
    weather_handler, 
    collect_input as collect_weather_input,
    WeatherError
)
from .calculator_tool import (
    create_calculator_tool, 
    calculator_handler, 
    collect_input as collect_calculator_input,
    CalculatorError
)
from .fs_tool import (
    create_fs_tool, 
    fs_handler, 
    collect_input as collect_filesystem_input,
    FSError
)


async def run_weather_example(executor: ToolExecutor) -> None:
    """Run a weather-only example.
    
    Args:
        executor: The tool executor
    """
    try:
        params = await collect_weather_input()
        result = await executor.execute_tool("get_weather", params)
        print("\nWeather information:")
        print(result)
    except WeatherError as e:
        print(f"Weather error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


async def run_calculator_example(executor: ToolExecutor) -> None:
    """Run a calculator-only example.
    
    Args:
        executor: The tool executor
    """
    try:
        params = await collect_calculator_input()
        result = await executor.execute_tool("calculator", params)
        print("\nCalculation result:")
        print(result)
    except CalculatorError as e:
        print(f"Calculator error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


async def run_filesystem_example(executor: ToolExecutor) -> None:
    """Run a filesystem-only example.
    
    Args:
        executor: The tool executor
    """
    try:
        params = await collect_filesystem_input()
        result = await executor.execute_tool("filesystem", params)
        print("\nFilesystem operation result:")
        print(result)
    except FSError as e:
        print(f"Filesystem error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


async def _initialize_chat() -> List[Dict[str, str]]:
    """Initialize chat with system message.
    
    Returns:
        Initial chat messages
    """
    return [{
        "role": "system",
        "content": (
            "You are a helpful assistant that can provide weather information, "
            "perform calculations, and access the local filesystem. When accessing "
            "the filesystem, always confirm with the user before executing destructive "
            "operations like deleting files or writing to existing files."
        )
    }]


async def run_chat(
    integration: Optional[LLMToolIntegration] = None,
    *,
    model_provider: str = "openai"
) -> None:
    """Run a chat with an LLM using all tools.
    
    Args:
        integration: Optional pre-configured LLM tool integration
        model_provider: The model provider to use ("openai" or "anthropic")
    """
    # Map providers to their API key environment variables
    api_key_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY"
    }
    model_names = {
        "openai": "GPT",
        "anthropic": "Claude"
    }
    
    api_key_var = api_key_vars.get(model_provider)
    if not api_key_var:
        print(f"Invalid model provider: {model_provider}")
        return
        
    if api_key_var not in os.environ:
        print(f"{model_names[model_provider]} API key not found!")
        print(f"Please set the {api_key_var} environment variable.")
        return
        
    # Create integration if not provided
    if integration is None:
        registry, api_key = _setup_tools()
        executor = _setup_executor(registry, api_key)
        integration = LLMToolIntegration(registry, executor, model_provider=model_provider)
        
    print(f"\nStarting chat with {model_names[model_provider]} (type 'exit' to quit):")
    messages = await _initialize_chat()
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() == "exit":
                break
                
            messages.append({"role": "user", "content": user_input})
            
            print("Assistant is thinking...")
            response = await integration.run_conversation(messages)
            
            print(f"Assistant: {response}")
            messages.append({"role": "assistant", "content": response})
            
    except Exception as e:
        print(f"Error in chat: {str(e)}")


async def run_llm_chat(integration: Optional[LLMToolIntegration] = None) -> None:
    """Run a chat with OpenAI's GPT using all tools.
    
    Args:
        integration: Optional pre-configured LLM tool integration
    """
    await run_chat(integration, model_provider="openai")


async def run_claude_chat(integration: Optional[LLMToolIntegration] = None) -> None:
    """Run a chat with Anthropic's Claude using all tools.
    
    Args:
        integration: Optional pre-configured LLM tool integration
    """
    await run_chat(integration, model_provider="anthropic")


def _setup_tools() -> tuple[ToolRegistry, Optional[str]]:
    """Set up tool registry and check API keys.
    
    Returns:
        Tuple of (registry, api_key)
    """
    registry = ToolRegistry()
    
    # Check if the weather API key is set
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if api_key:
        weather_tool = create_weather_tool()
        registry.register_tool(weather_tool)
        print("Weather tool registered")
    else:
        print("OpenWeatherMap API key not found. Weather tool will not be available.")
        print("Set the OPENWEATHERMAP_API_KEY environment variable to enable it.")
    
    # Register calculator tool
    calculator_tool = create_calculator_tool()
    registry.register_tool(calculator_tool)
    print("Calculator tool registered")
    
    # Register filesystem tool
    filesystem_tool = create_fs_tool()
    registry.register_tool(filesystem_tool)
    print("Filesystem tool registered")
    
    return registry, api_key


def _setup_executor(registry: ToolRegistry, api_key: Optional[str]) -> ToolExecutor:
    """Set up tool executor with handlers.
    
    Args:
        registry: The tool registry
        api_key: Optional weather API key
        
    Returns:
        Configured tool executor
    """
    executor = ToolExecutor(registry)
    
    if api_key:
        executor.register_handler("get_weather", weather_handler)
    
    executor.register_handler("calculator", calculator_handler)
    executor.register_handler("filesystem", fs_handler)
    
    return executor


async def main() -> None:
    """Run an example conversation with multiple tools."""
    # Set up tools and executor
    registry, api_key = _setup_tools()
    executor = _setup_executor(registry, api_key)

    # Interactive mode
    print("\nAvailable modes:")
    print("1 = Weather tool (requires API key)")
    print("2 = Calculator tool")
    print("3 = Filesystem tool")
    print("4 = Chat with GPT (requires OpenAI API key)")
    print("5 = Chat with Claude (requires Anthropic API key)")
    
    mode = input("\nChoose mode (1-5): ")
    
    if mode == "1" and api_key:
        await run_weather_example(executor)
    elif mode == "1" and not api_key:
        print("Weather tool is not available without an API key.")
    elif mode == "2":
        await run_calculator_example(executor)
    elif mode == "3":
        await run_filesystem_example(executor)
    elif mode == "4":
        await run_llm_chat()
    elif mode == "5":
        await run_claude_chat()
    else:
        print(f"Invalid mode: {mode}")


if __name__ == "__main__":
    asyncio.run(main()) 