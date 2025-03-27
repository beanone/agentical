"""Example implementations of various tools using the Agentical framework.

This module demonstrates the integration and usage of multiple tools:
- Weather tool: Fetches weather information using OpenWeatherMap API
- Calculator tool: Performs basic arithmetic calculations
- Filesystem tool: Handles basic file system operations

The tools can be used either:
1. Individually through dedicated functions
2. Together through an LLM-powered chat interface (supports OpenAI GPT and Anthropic Claude)

Example:
    ```python
    def main():
        registry, api_key = _setup_tools()
        executor = _setup_executor(registry, api_key)
        run_calculator_example(executor)
    ```

Note:
    Some tools require API keys set in environment variables:
    - OPENWEATHERMAP_API_KEY: For weather information
    - OPENAI_API_KEY: For GPT chat interface
    - ANTHROPIC_API_KEY: For Claude chat interface
"""

# Standard library imports
import asyncio
import os
from typing import Dict, Any, List, Optional, Literal

# Constants
WEATHER_API_KEY = "OPENWEATHERMAP_API_KEY"
ModelProvider = Literal["openai", "anthropic"]

PROVIDER_CONFIG = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "display_name": "GPT",
        "default_model": "gpt-4-turbo-preview"
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "display_name": "Claude",
        "default_model": "claude-3-sonnet-20240229"
    }
}

SYSTEM_PROMPT = (
    "You are a helpful assistant that can provide weather information, "
    "perform calculations, and access the local filesystem. When accessing "
    "the filesystem, always confirm with the user before executing destructive "
    "operations like deleting files or writing to existing files."
)

# Local imports
from agentical.core import ToolRegistry, ToolExecutor, ProviderConfig
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
    """Run an interactive weather information example.
    
    This function prompts the user for location and unit preferences,
    then fetches and displays the current weather information.
    
    Args:
        executor: The tool executor instance with weather tool registered
        
    Raises:
        WeatherError: If there's an error fetching weather data
        Exception: For other unexpected errors
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
    """Run an interactive calculator example.
    
    This function prompts the user for a mathematical expression,
    evaluates it safely, and displays the result.
    
    Args:
        executor: The tool executor instance with calculator tool registered
        
    Raises:
        CalculatorError: If the expression is invalid or unsafe
        Exception: For other unexpected errors
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
    """Run an interactive filesystem operation example.
    
    This function prompts the user for filesystem operation details
    (read/write/list) and executes the requested operation.
    
    Args:
        executor: The tool executor instance with filesystem tool registered
        
    Raises:
        FSError: If there's an error with the filesystem operation
        Exception: For other unexpected errors
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


def _initialize_chat() -> List[Dict[str, str]]:
    """Initialize chat with system message.
    
    Creates the initial message list with a system message that defines
    the assistant's capabilities and safety guidelines.
    
    Returns:
        List[Dict[str, str]]: Initial chat messages with system prompt
    """
    return [{
        "role": "system",
        "content": SYSTEM_PROMPT
    }]


async def run_chat(
    integration: Optional[LLMToolIntegration] = None,
    *,
    model_provider: ModelProvider = "openai"
) -> None:
    """Run an interactive chat session with an LLM using all available tools.
    
    This function sets up a chat interface where users can interact with an LLM
    that has access to weather, calculator, and filesystem tools. The chat
    continues until the user types 'exit'.
    
    Args:
        integration: Optional pre-configured LLM tool integration. If None,
            a new integration will be created with default settings.
        model_provider: The model provider to use, either "openai" or "anthropic".
            Defaults to "openai".
            
    Note:
        Requires appropriate API keys to be set in environment variables:
        - OPENAI_API_KEY for "openai" provider
        - ANTHROPIC_API_KEY for "anthropic" provider
    """
    if model_provider not in PROVIDER_CONFIG:
        print(f"Invalid model provider: {model_provider}")
        print(f"Supported providers: {', '.join(PROVIDER_CONFIG.keys())}")
        return
        
    config = PROVIDER_CONFIG[model_provider]
    if config["api_key_env"] not in os.environ:
        print(f"{config['display_name']} API key not found!")
        print(f"Please set the {config['api_key_env']} environment variable.")
        return
        
    # Create integration if not provided
    if integration is None:
        try:
            registry, api_key = _setup_tools()
            executor = _setup_executor(registry, api_key)
            
            # Create provider config
            provider_config = ProviderConfig(
                api_key=os.environ[config["api_key_env"]],
                model=config["default_model"]
            )
            
            integration = LLMToolIntegration(
                registry=registry,
                executor=executor,
                provider_config=provider_config,
                model_provider=model_provider
            )
        except Exception as e:
            print(f"Failed to initialize LLM integration: {str(e)}")
            return
        
    print(f"\nStarting chat with {config['display_name']} (type 'exit' to quit):")
    messages = _initialize_chat()
    
    try:
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() == "exit":
                    break
                    
                messages.append({"role": "user", "content": user_input})
                
                print("Assistant is thinking...")
                response = await integration.run_conversation(messages)
                
                print(f"Assistant: {response}")
                messages.append({"role": "assistant", "content": response})
            except KeyboardInterrupt:
                print("\nChat interrupted by user.")
                break
            except Exception as e:
                print(f"Error in conversation: {str(e)}")
                print("You can continue chatting or type 'exit' to quit.")
                
    except Exception as e:
        print(f"Fatal error in chat: {str(e)}")


async def run_llm_chat(integration: Optional[LLMToolIntegration] = None) -> None:
    """Run an interactive chat session with OpenAI GPT.
    
    This is a convenience wrapper around run_chat() that defaults to
    using the OpenAI GPT model.
    
    Args:
        integration: Optional pre-configured LLM tool integration
    """
    await run_chat(integration, model_provider="openai")


async def run_claude_chat(integration: Optional[LLMToolIntegration] = None) -> None:
    """Run an interactive chat session with Anthropic Claude.
    
    This is a convenience wrapper around run_chat() that defaults to
    using the Anthropic Claude model.
    
    Args:
        integration: Optional pre-configured LLM tool integration
    """
    await run_chat(integration, model_provider="anthropic")


def _setup_tools() -> tuple[ToolRegistry, Optional[str]]:
    """Set up and configure all available tools.
    
    This function:
    1. Creates a new tool registry
    2. Checks for weather API key and registers weather tool if available
    3. Registers calculator and filesystem tools
    
    Returns:
        tuple[ToolRegistry, Optional[str]]: A tuple containing:
            - The configured tool registry
            - The weather API key if available, None otherwise
    """
    registry = ToolRegistry()
    
    # Check if the weather API key is set
    api_key = os.environ.get(WEATHER_API_KEY)
    if api_key:
        try:
            weather_tool = create_weather_tool()
            registry.register_tool(weather_tool)
            print("Weather tool registered")
        except Exception as e:
            print(f"Failed to register weather tool: {str(e)}")
            api_key = None
    else:
        print(f"{WEATHER_API_KEY} not found. Weather tool will not be available.")
        print(f"Set the {WEATHER_API_KEY} environment variable to enable it.")
    
    try:
        # Register calculator tool
        calculator_tool = create_calculator_tool()
        registry.register_tool(calculator_tool)
        print("Calculator tool registered")
        
        # Register filesystem tool
        filesystem_tool = create_fs_tool()
        registry.register_tool(filesystem_tool)
        print("Filesystem tool registered")
    except Exception as e:
        print(f"Failed to register tools: {str(e)}")
        raise
    
    return registry, api_key


def _setup_executor(registry: ToolRegistry, api_key: Optional[str]) -> ToolExecutor:
    """Set up and configure the tool executor with appropriate handlers.
    
    This function creates a new executor and registers handlers for all
    available tools. The weather handler is only registered if an API key
    is provided.
    
    Args:
        registry: The tool registry containing all registered tools
        api_key: Optional weather API key. If provided, the weather
            handler will be registered
            
    Returns:
        ToolExecutor: The configured tool executor
    """
    executor = ToolExecutor(registry)
    
    if api_key:
        executor.register_handler("get_weather", weather_handler)
    
    executor.register_handler("calculator", calculator_handler)
    executor.register_handler("filesystem", fs_handler)
    
    return executor


async def main() -> None:
    """Main entry point for the example application.
    
    This function sets up the tools and allows the user to choose
    which example to run:
    1. Weather information tool
    2. Calculator tool
    3. Filesystem operations tool
    4. Chat with GPT (OpenAI)
    5. Chat with Claude (Anthropic)
    """
    print("\nAvailable modes:")
    print("1 = Weather tool (requires API key)")
    print("2 = Calculator tool")
    print("3 = Filesystem tool")
    print("4 = Chat with GPT (requires OpenAI API key)")
    print("5 = Chat with Claude (requires Anthropic API key)")
    
    mode = input("Select mode (1-5): ").strip()
    
    registry, api_key = _setup_tools()
    executor = _setup_executor(registry, api_key)
    
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