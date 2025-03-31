"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import json
import sys
from pathlib import Path
import argparse

from dotenv import load_dotenv

from agentical.api.llm_backend import LLMBackend
from agentical.mcp.provider import MCPToolProvider

# Load environment variables (including GEMINI_API_KEY)
load_dotenv()


def parse_arguments():
    """Parse command line arguments, matching client.py behavior."""
    parser = argparse.ArgumentParser(description='MCP Tool Provider Test')
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Path to MCP configuration file (default: config.json)'
    )
    return parser.parse_args()


async def chat_loop(provider: MCPToolProvider):
    """Run an interactive chat session with the user."""
    print("\nMCP Tool Provider Started! Type 'quit' to exit.")
    
    while True:
        query = input("\nQuery: ").strip()
        if query.lower() == 'quit':
            break
            
        try:
            # Process the user's query and display the response
            response = await provider.process_query(query)
            print("\n" + response)
        except Exception as e:
            print(f"\nError processing query: {str(e)}")


async def interactive_server_selection(provider: MCPToolProvider) -> str | None:
    """Interactively prompt the user to select an MCP server.
    
    Returns:
        Selected server name or None if all servers are selected
    """
    servers = provider.list_available_servers()
    
    if not servers:
        raise ValueError("No MCP servers available in configuration")
        
    print("\nAvailable MCP servers:")
    for idx, server in enumerate(servers, 1):
        print(f"{idx}. {server}")
    
    # Add the "All above servers" option
    all_servers_idx = len(servers) + 1
    print(f"{all_servers_idx}. All above servers")
        
    while True:
        try:
            choice = input("\nSelect a server (enter number): ").strip()
            idx = int(choice) - 1
            
            # Check if "All above servers" was selected
            if idx == len(servers):
                return None
                
            if 0 <= idx < len(servers):
                return servers[idx]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


async def run_demo(llm_backend: LLMBackend):
    """Main function to test MCPToolProvider functionality."""
    # Parse command line arguments
    args = parse_arguments()
    config_path = args.config
    
    # Check if configuration file exists
    if not Path(config_path).exists():
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please provide a valid configuration file using --config or -c option.")
        print("Example: python test_mcp_provider.py --config my_config.json")
        sys.exit(1)
    
    # Initialize provider with the Gemini backend
    provider = MCPToolProvider(llm_backend=llm_backend)
    
    try:
        # Load configurations
        print(f"\nLoading MCP configurations from: {config_path}")
        provider.available_servers = provider.load_mcp_config(config_path)
        print(f"Loaded {len(provider.available_servers)} servers")
        
        # Let user select server
        selected_server = await interactive_server_selection(provider)
        
        # Connect to selected server(s)
        if selected_server is None:
            # Connect to all servers
            print("\nConnecting to all servers...")
            results = await provider.mcp_connect_all()
            
            # Print connection results
            for server_name, error in results:
                if error:
                    print(f"Failed to connect to {server_name}: {error}")
                else:
                    print(f"Successfully connected to {server_name}")
                    
            # Check if at least one connection was successful
            if not any(error is None for _, error in results):
                raise Exception("Failed to connect to any servers")
        else:
            # Connect to single selected server
            await provider.mcp_connect(selected_server)
        
        # Start chat loop
        await chat_loop(provider)
        
    except json.JSONDecodeError:
        print(f"Error: '{config_path}' is not a valid JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        # Ensure cleanup
        await provider.cleanup()
