"""Test script for MCPToolProvider with Anthropic backend."""

import asyncio
import json
import sys
from pathlib import Path
import argparse
import logging
import os

from dotenv import load_dotenv

from anthropic_backend.anthropic_chat import AnthropicBackend
from agentical.integration.mcp.provider import MCPToolProvider

# # Configure debug logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )

# Enable debug logging for schema adapter
logging.getLogger('anthropic_backend.schema_adapter').setLevel(logging.DEBUG)
logging.getLogger('anthropic_backend.anthropic_chat').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Load environment variables (including ANTHROPIC_API_KEY)
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


async def main():
    """Main function to test MCPToolProvider functionality."""
    # Parse command line arguments
    args = parse_arguments()
    config_path = args.config
    
    # Check if configuration file exists
    if not Path(config_path).exists():
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please provide a valid configuration file using --config or -c option.")
        print("Example: python test_anthropic.py --config my_config.json")
        sys.exit(1)
        
    # Initialize the Anthropic backend
    llm_backend = AnthropicBackend()
    
    # Initialize provider with the Anthropic backend
    provider = MCPToolProvider(llm_backend=llm_backend)
    
    try:
        # Load configurations
        print(f"\nLoading MCP configurations from: {config_path}")
        provider.available_servers = provider.load_mcp_config(config_path)
        print(f"Loaded {len(provider.available_servers)} servers")
        
        # Let user select server
        selected_server = await provider.interactive_server_selection()
        
        # Connect to selected server
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


if __name__ == "__main__":
    asyncio.run(main()) 