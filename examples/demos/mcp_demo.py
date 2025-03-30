#!/usr/bin/env python3
"""
Demo script showing how to use MCP as a model provider with LLMToolIntegration.
Similar to examples.py but using MCP instead of OpenAI.
"""

import asyncio
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Tuple

from agentical.core import ToolRegistry, ToolExecutor, ProviderConfig
from agentical.providers.llm import LLMToolIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_mcp_config() -> Dict[str, Any]:
    """Load MCP configuration from .mcp-demo.json file."""
    config_path = Path(__file__).parent / ".mcp-demo.json"
    if not config_path.exists():
        raise FileNotFoundError(f"MCP config file not found at {config_path}")
    
    with open(config_path) as f:
        config = json.load(f)
    return config["mcpServers"]

def adjust_server_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adjust server configuration based on the platform.
    
    Args:
        config: Original server configuration
        
    Returns:
        Adjusted configuration for the current platform
    """
    adjusted_config = config.copy()
    
    # If we're on Windows and the command is 'cmd', keep as is
    if platform.system() == "Windows" and config["command"] == "cmd":
        return adjusted_config
    
    # If we're on Unix-like system and the command is 'cmd', adjust to use npx directly
    if platform.system() != "Windows" and config["command"] == "cmd":
        # Remove 'cmd', '/c' and keep only the npx command and its args
        adjusted_config["command"] = "npx"
        adjusted_config["args"] = config["args"][2:]  # Skip 'cmd' and '/c'
        logger.info("Adjusted Windows command for Unix-like system")
    
    return adjusted_config

def select_mcp_server(servers: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Prompt user to select an MCP server from available configurations.
    
    Args:
        servers: Dictionary of available MCP server configurations
        
    Returns:
        Tuple of (selected server name, server configuration)
    """
    print("\nAvailable MCP servers:")
    for i, (name, _) in enumerate(servers.items(), 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            choice = int(input("\nSelect a server (enter number): "))
            if 1 <= choice <= len(servers):
                server_name = list(servers.keys())[choice - 1]
                return server_name, servers[server_name]
            print(f"Please enter a number between 1 and {len(servers)}")
        except ValueError:
            print("Please enter a valid number")

async def main() -> None:
    """Main demo function showing MCP provider with LLMToolIntegration."""
    # Load MCP configuration
    mcp_servers = load_mcp_config()
    
    # Let user select which server to use
    server_name, server_config = select_mcp_server(mcp_servers)
    logger.info(f"Using MCP server: {server_name}")
    
    # Adjust configuration for current platform
    server_config = adjust_server_config(server_config)
    
    # Set up tool registry and executor
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    
    # Create configuration for MCP provider
    provider_config = ProviderConfig(
        api_key="not-needed-for-mcp",  # MCP doesn't need an API key
        model="test-model",
        extra_config={
            "command": server_config["command"],
            "args": server_config["args"],
            "workingDir": None,  # Use default working directory
            "env": None  # Use default environment
        }
    )

    # Create LLM integration with tools
    integration = LLMToolIntegration(
        registry=registry,
        executor=executor,
        provider_config=provider_config,
        model_provider="mcp"  # Using MCP instead of OpenAI/Anthropic
    )
    
    # Example conversation using MCP server's tools
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can use tools."
        },
        {
            "role": "user",
            "content": "What tools are available?"
        }
    ]
    
    response = await integration.run_conversation(messages)
    print(f"\nResponse: {response}\n")

if __name__ == "__main__":
    asyncio.run(main()) 