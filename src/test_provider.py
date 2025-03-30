"""Test script for the new MCPToolProvider implementation."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from agentical.integration.mcp.provider import MCPToolProvider

# Load environment variables from .env file
load_dotenv()

async def main():
    # Initialize the provider
    provider = MCPToolProvider()
    
    # Load MCP config from experiment directory
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    provider.available_servers = MCPToolProvider.load_mcp_config(config_path)
    print(f"\nLoaded {len(provider.available_servers)} servers from configuration")
    
    try:
        # Let user select a server
        server_name = await provider.interactive_server_selection()
        
        # Connect to the selected server
        await provider.mcp_connect(server_name)
        
        # Process a test query
        query = "What files are in the current directory?"
        print(f"\nSending query: {query}")
        
        response = await provider.process_query(query)
        print(f"\nResponse: {response}")
        
    finally:
        # Clean up resources
        await provider.cleanup()

if __name__ == "__main__":
    # Ensure PYTHONPATH includes our src directory
    src_path = str(Path(__file__).parent.absolute())
    if src_path not in os.environ.get("PYTHONPATH", ""):
        os.environ["PYTHONPATH"] = f"{src_path}:{os.environ.get('PYTHONPATH', '')}"
    
    asyncio.run(main()) 