"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import json
import sys
from pathlib import Path
import argparse

from dotenv import load_dotenv

from openai_backend.openai_chat import OpenAIBackend
from agentical.integration.mcp.provider import MCPToolProvider

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
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Use interactive server selection mode (default: connect to all servers)'
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
        print("Example: python test_mcp_provider.py --config my_config.json")
        sys.exit(1)
        
    # Initialize the OpenAI backend
    llm_backend = OpenAIBackend()
    
    # Initialize provider with the OpenAI backend
    provider = MCPToolProvider(llm_backend=llm_backend)
    
    try:
        # Load configurations
        print(f"\nLoading MCP configurations from: {config_path}")
        provider.available_servers = provider.load_mcp_config(config_path)
        print(f"Loaded {len(provider.available_servers)} servers")
        
        # Connect to servers based on mode
        if args.interactive:
            await provider.interactive_server_selection()
        else:
            await provider.connect()
        
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