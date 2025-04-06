"""Interactive chat client for MCP Tool Provider."""

import argparse
import logging
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider
from agentical.mcp.config import FileBasedMCPConfigProvider
from agentical.utils.log_utils import redact_sensitive_data, sanitize_log_message

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP Tool Provider Chat Client")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.json",
        help="Path to MCP configuration file"
    )
    return parser.parse_args()

async def chat_loop(provider: MCPToolProvider):
    """Run an interactive chat session with the user."""
    start_time = time.time()
    logger.info("Starting chat session")
    print("\nMCP Tool Provider Started! Type 'quit' to exit.")
    
    query_count = 0
    error_count = 0
    
    try:
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                logger.info("User requested to quit chat session")
                break
                
            query_count += 1
            query_start = time.time()
            try:
                # Process the user's query and display the response
                logger.debug("Processing user query", extra=redact_sensitive_data({
                    "query": query,
                    "query_number": query_count
                }))
                response = await provider.process_query(query)
                query_duration = time.time() - query_start
                logger.debug("Query processed", extra={
                    "query_number": query_count,
                    "duration_ms": int(query_duration * 1000)
                })
                print("\n" + response)
            except Exception as e:
                error_count += 1
                query_duration = time.time() - query_start
                logger.error("Query processing error", extra={
                    "query_number": query_count,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(query_duration * 1000)
                }, exc_info=True)
                print(f"\nError processing query: {str(e)}")
    finally:
        # Ensure cleanup happens before ending the session
        logger.info("Starting chat session cleanup")
        try:
            await provider.cleanup()
        except Exception as e:
            logger.error("Error during chat session cleanup", extra={
                "error": sanitize_log_message(str(e))
            })
        
        session_duration = time.time() - start_time
        logger.info("Chat session ended", extra={
            "total_queries": query_count,
            "successful_queries": query_count - error_count,
            "failed_queries": error_count,
            "duration_ms": int(session_duration * 1000)
        })

async def interactive_server_selection(provider: MCPToolProvider) -> str | None:
    """Interactively prompt the user to select an MCP server."""
    start_time = time.time()
    logger.debug("Starting server selection")
    servers = provider.list_available_servers()
    
    if not servers:
        logger.error("No servers found in configuration")
        raise ValueError("No MCP servers available in configuration")
        
    logger.debug("Displaying server options", extra={
        "num_servers": len(servers),
        "servers": servers
    })
    print("\nAvailable MCP servers:")
    for idx, server in enumerate(servers, 1):
        print(f"{idx}. {server}")
    
    # Add the "All above servers" option
    all_servers_idx = len(servers) + 1
    print(f"{all_servers_idx}. All above servers")
    
    attempts = 0
    while True:
        attempts += 1
        try:
            choice = input("\nSelect a server (enter number): ").strip()
            logger.debug("Processing user selection", extra={
                "attempt": attempts,
                "raw_input": choice
            })
            idx = int(choice) - 1
            
            # Check if "All above servers" was selected
            if idx == len(servers):
                duration = time.time() - start_time
                logger.info("All servers selected", extra={
                    "attempts": attempts,
                    "duration_ms": int(duration * 1000)
                })
                return None
                
            if 0 <= idx < len(servers):
                selected = servers[idx]
                duration = time.time() - start_time
                logger.info("Server selected", extra={
                    "selected_server": selected,
                    "attempts": attempts,
                    "duration_ms": int(duration * 1000)
                })
                return selected
                
            logger.warning("Invalid selection", extra={
                "attempt": attempts,
                "input": choice,
                "max_valid": all_servers_idx
            })
            print("Invalid selection. Please try again.")
        except ValueError:
            logger.warning("Invalid input format", extra={
                "attempt": attempts,
                "input": choice
            })
            print("Please enter a valid number.")

async def run_demo(llm_backend: LLMBackend):
    """Main function to test MCPToolProvider functionality."""
    start_time = time.time()
    logger.info("Starting MCP Tool Provider demo", extra={
        "llm_backend_type": type(llm_backend).__name__
    })
    
    # Parse command line arguments
    args = parse_arguments()
    config_path = args.config
    
    # Check if configuration file exists
    if not Path(config_path).exists():
        logger.error("Configuration file not found", extra={
            "config_path": config_path
        })
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please provide a valid configuration file using --config or -c option.")
        print("Example: python test_mcp_provider.py --config my_config.json")
        sys.exit(1)
    
    # Initialize provider with the LLM backend and config
    logger.debug("Initializing provider", extra={
        "config_path": config_path,
        "llm_backend_type": type(llm_backend).__name__
    })
    config_provider = FileBasedMCPConfigProvider(config_path)
    provider = MCPToolProvider(llm_backend=llm_backend, config_provider=config_provider)
    
    try:
        # Initialize provider and load configurations
        logger.info("Loading configurations", extra={
            "config_path": config_path
        })
        await provider.initialize()
        num_servers = len(provider.available_servers)
        logger.info("Configurations loaded", extra={
            "num_servers": num_servers
        })
        print(f"\nLoaded {num_servers} servers")
        
        # Let user select server
        selected_server = await interactive_server_selection(provider)
        
        # Connect to selected server(s)
        connection_start = time.time()
        if selected_server is None:
            # Connect to all servers
            logger.info("Connecting to all servers")
            print("\nConnecting to all servers...")
            results = await provider.mcp_connect_all()
            
            # Print connection results
            success_count = 0
            for server_name, error in results:
                if error:
                    logger.error("Server connection failed", extra={
                        "server_name": server_name,
                        "error": sanitize_log_message(str(error))
                    })
                    print(f"Failed to connect to {server_name}: {error}")
                else:
                    logger.info("Server connection successful", extra={
                        "server_name": server_name
                    })
                    print(f"Successfully connected to {server_name}")
                    success_count += 1
                    
            # Check if at least one connection was successful
            if success_count == 0:
                connection_duration = time.time() - connection_start
                logger.error("All connections failed", extra={
                    "num_servers": len(results),
                    "duration_ms": int(connection_duration * 1000)
                })
                raise Exception("Failed to connect to any servers")
                
            connection_duration = time.time() - connection_start
            logger.info("Server connections completed", extra={
                "successful": success_count,
                "failed": len(results) - success_count,
                "duration_ms": int(connection_duration * 1000)
            })
        else:
            # Connect to single selected server
            logger.info("Connecting to server", extra={
                "server_name": selected_server
            })
            await provider.mcp_connect(selected_server)
            connection_duration = time.time() - connection_start
            logger.info("Server connection successful", extra={
                "server_name": selected_server,
                "duration_ms": int(connection_duration * 1000)
            })
        
        # Start chat loop
        await chat_loop(provider)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error("Demo execution failed", extra={
            "error": sanitize_log_message(str(e)),
            "duration_ms": int(duration * 1000)
        })
        raise
    finally:
        # Ensure cleanup happens before exiting
        logger.info("Starting demo cleanup")
        try:
            await provider.cleanup()
        except Exception as e:
            logger.error("Error during demo cleanup", extra={
                "error": sanitize_log_message(str(e))
            })
        
        duration = time.time() - start_time
        logger.info("Demo execution completed", extra={
            "duration_ms": int(duration * 1000)
        })
