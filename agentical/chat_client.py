"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import json
import logging
import sys
from pathlib import Path
import argparse

from dotenv import load_dotenv

from agentical.api.llm_backend import LLMBackend
from agentical.mcp.provider import MCPToolProvider

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables (including GEMINI_API_KEY)
load_dotenv()


def parse_arguments():
    """Parse command line arguments, matching client.py behavior."""
    logger.debug("Parsing command line arguments")
    parser = argparse.ArgumentParser(description='MCP Tool Provider Test')
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Path to MCP configuration file (default: config.json)'
    )
    args = parser.parse_args()
    logger.debug("Parsed arguments: config_path=%s", args.config)
    return args


async def chat_loop(provider: MCPToolProvider):
    """Run an interactive chat session with the user."""
    logger.info("Starting interactive chat session")
    print("\nMCP Tool Provider Started! Type 'quit' to exit.")
    
    while True:
        query = input("\nQuery: ").strip()
        if query.lower() == 'quit':
            logger.info("User requested to quit chat session")
            break
            
        try:
            # Process the user's query and display the response
            logger.debug("Processing user query: %s", query)
            response = await provider.process_query(query)
            logger.debug("Received response: %s", response)
            print("\n" + response)
        except Exception as e:
            logger.error("Error processing query: %s", str(e), exc_info=True)
            print(f"\nError processing query: {str(e)}")

    logger.info("Chat session ended")


async def interactive_server_selection(provider: MCPToolProvider) -> str | None:
    """Interactively prompt the user to select an MCP server.
    
    Returns:
        Selected server name or None if all servers are selected
    """
    logger.debug("Starting server selection")
    servers = provider.list_available_servers()
    
    if not servers:
        logger.error("No MCP servers found in configuration")
        raise ValueError("No MCP servers available in configuration")
        
    logger.debug("Available servers: %s", servers)
    print("\nAvailable MCP servers:")
    for idx, server in enumerate(servers, 1):
        print(f"{idx}. {server}")
    
    # Add the "All above servers" option
    all_servers_idx = len(servers) + 1
    print(f"{all_servers_idx}. All above servers")
        
    while True:
        try:
            choice = input("\nSelect a server (enter number): ").strip()
            logger.debug("User selected: %s", choice)
            idx = int(choice) - 1
            
            # Check if "All above servers" was selected
            if idx == len(servers):
                logger.info("User selected all servers")
                return None
                
            if 0 <= idx < len(servers):
                selected = servers[idx]
                logger.info("User selected server: %s", selected)
                return selected
                
            logger.warning("Invalid server selection: %s", choice)
            print("Invalid selection. Please try again.")
        except ValueError:
            logger.warning("Invalid input format: %s", choice)
            print("Please enter a valid number.")


async def run_demo(llm_backend: LLMBackend):
    """Main function to test MCPToolProvider functionality."""
    logger.info("Starting MCP Tool Provider demo")
    
    # Parse command line arguments
    args = parse_arguments()
    config_path = args.config
    
    # Check if configuration file exists
    if not Path(config_path).exists():
        logger.error("Configuration file not found: %s", config_path)
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please provide a valid configuration file using --config or -c option.")
        print("Example: python test_mcp_provider.py --config my_config.json")
        sys.exit(1)
    
    # Initialize provider with the LLM backend
    logger.debug("Initializing MCPToolProvider with %s", type(llm_backend).__name__)
    provider = MCPToolProvider(llm_backend=llm_backend)
    
    try:
        # Load configurations
        logger.info("Loading MCP configurations from: %s", config_path)
        provider.available_servers = provider.load_mcp_config(config_path)
        logger.info("Loaded %d servers", len(provider.available_servers))
        print(f"\nLoading MCP configurations from: {config_path}")
        print(f"Loaded {len(provider.available_servers)} servers")
        
        # Let user select server
        selected_server = await interactive_server_selection(provider)
        
        # Connect to selected server(s)
        if selected_server is None:
            # Connect to all servers
            logger.info("Connecting to all available servers")
            print("\nConnecting to all servers...")
            results = await provider.mcp_connect_all()
            
            # Print connection results
            success_count = 0
            for server_name, error in results:
                if error:
                    logger.error("Failed to connect to %s: %s", server_name, error)
                    print(f"Failed to connect to {server_name}: {error}")
                else:
                    logger.info("Successfully connected to %s", server_name)
                    print(f"Successfully connected to {server_name}")
                    success_count += 1
                    
            # Check if at least one connection was successful
            if success_count == 0:
                logger.error("Failed to connect to any servers")
                raise Exception("Failed to connect to any servers")
            logger.info("Connected to %d out of %d servers", success_count, len(results))
        else:
            # Connect to single selected server
            logger.info("Connecting to selected server: %s", selected_server)
            await provider.mcp_connect(selected_server)
            logger.info("Successfully connected to %s", selected_server)
        
        # Start chat loop
        await chat_loop(provider)
        
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in configuration file: %s - %s", config_path, str(e))
        print(f"Error: '{config_path}' is not a valid JSON file.")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        # Ensure cleanup
        logger.info("Cleaning up resources")
        await provider.cleanup()
        logger.info("Demo completed")
