"""Connection management for MCP servers.

This module provides a centralized connection management system for MCP (Machine Control Protocol) servers.
It handles both WebSocket and stdio-based connections, with features including:
- Automatic connection retry with exponential backoff
- Resource cleanup and management
- Connection state tracking
- Error handling and logging

Example:
    ```python
    from contextlib import AsyncExitStack
    from agentical.mcp.connection import MCPConnectionManager
    from agentical.mcp.schemas import ServerConfig

    async def connect_to_server():
        async with AsyncExitStack() as stack:
            manager = MCPConnectionManager(stack)
            config = ServerConfig(
                command="server_command",
                args=["--port", "8080"],
                is_websocket=False
            )
            try:
                session = await manager.connect("my_server", config)
                # Use session...
            finally:
                await manager.cleanup("my_server")
    ```

Implementation Notes:
    - Uses AsyncExitStack for proper async resource management
    - Implements automatic retry with backoff for connection stability
    - Maintains connection state to prevent duplicate connections
    - Handles both WebSocket and stdio server types
    - Provides comprehensive error handling and logging
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Dict, Any, Optional, Tuple

import backoff
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agentical.mcp.schemas import ServerConfig

logger = logging.getLogger(__name__)

class MCPConnectionManager:
    """Manages connections to MCP servers.
    
    This class provides a centralized way to manage connections to MCP servers,
    handling connection establishment, maintenance, and cleanup. It supports both
    WebSocket and stdio-based connections, with automatic retry capabilities.
    
    Attributes:
        MAX_RETRIES (int): Maximum number of connection retry attempts
        BASE_DELAY (float): Base delay in seconds between retry attempts
        sessions (Dict[str, ClientSession]): Active server sessions
        stdios (Dict[str, Any]): stdio transport handlers
        writes (Dict[str, Any]): Write transport handlers
        
    Implementation Notes:
        - Uses AsyncExitStack for proper async context management
        - Implements exponential backoff for connection retries
        - Maintains connection state to prevent duplicate connections
        - Provides comprehensive error handling and logging
        - Thread-safe for basic operations
        
    Example:
        ```python
        manager = MCPConnectionManager(AsyncExitStack())
        try:
            session = await manager.connect(
                "server1",
                ServerConfig(command="cmd", args=[])
            )
            # Use session...
        finally:
            await manager.cleanup("server1")
        ```
    """
    
    # Connection settings
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    
    def __init__(self, exit_stack: AsyncExitStack):
        """Initialize the connection manager.
        
        Args:
            exit_stack: AsyncExitStack for managing async context resources.
                       This should be provided by the caller to ensure proper
                       resource cleanup in the correct order.
        
        Note:
            The exit_stack should be managed by the caller to ensure proper
            cleanup order, especially when used with other async resources.
        """
        self.exit_stack = exit_stack
        self.sessions: Dict[str, ClientSession] = {}
        self.stdios: Dict[str, Any] = {}
        self.writes: Dict[str, Any] = {}
        
    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError),
        max_tries=MAX_RETRIES,
        base=BASE_DELAY
    )
    async def _connect_with_retry(self, server_name: str, server_params: StdioServerParameters) -> Tuple[ClientSession, Any, Any]:
        """Attempt to connect to a server with exponential backoff retry.
        
        This method implements a retry mechanism with exponential backoff for
        handling transient connection failures. It will retry up to MAX_RETRIES
        times, with increasing delays between attempts.
        
        Args:
            server_name: Name of the server to connect to
            server_params: Server connection parameters including command and args
            
        Returns:
            Tuple containing:
                - ClientSession: The established session
                - Any: stdio transport
                - Any: write transport
            
        Raises:
            ConnectionError: If all connection attempts fail
            TimeoutError: If connection attempts timeout
        """
        try:
            logger.debug("Establishing connection to %s", server_name)
            
            # Enter contexts directly in the main exit stack
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # Initialize session
            logger.debug("Initializing session for %s", server_name)
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # Initialize session
            await session.initialize()
            
            return session, stdio, write
            
        except Exception as e:
            logger.error("Connection attempt failed for %s: %s", server_name, str(e))
            # Let the exit stack handle cleanup of any initialized resources
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def connect(self, server_name: str, config: ServerConfig) -> ClientSession:
        """Connect to an MCP server.
        
        This is the main entry point for establishing server connections. It handles
        connections using the MCP protocol, which abstracts the underlying transport.
        
        Args:
            server_name: Name of the server to connect to. Must be unique.
            config: Server configuration containing connection details
            
        Returns:
            The established ClientSession for interacting with the server
            
        Raises:
            ConnectionError: If connection fails after retries
            ValueError: If server is already connected or invalid configuration
            
        Note:
            - Connections are automatically retried on failure
            - Resources are properly cleaned up on failure
        """
        if server_name in self.sessions:
            raise ValueError(f"Server {server_name} is already connected")
            
        try:
            return await self._handle_connection(server_name, config)
        except Exception as e:
            logger.error("Failed to connect to server %s: %s", server_name, str(e))
            await self.cleanup(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def _handle_connection(self, server_name: str, config: ServerConfig) -> ClientSession:
        """Handle connection to an MCP server.
        
        Creates and manages the server connection with appropriate parameters,
        letting the MCP protocol handle the underlying transport details.
        
        Args:
            server_name: Name of the server
            config: Server configuration
            
        Returns:
            The established ClientSession
            
        Raises:
            ConnectionError: If connection fails
        """
        params = {
            "command": config.command,
            "args": config.args
        }
        if config.env:
            params["env"] = config.env
            
        server_params = StdioServerParameters(**params)
        session, stdio, write = await self._connect_with_retry(server_name, server_params)
        
        # Store connection details
        self.sessions[server_name] = session
        self.stdios[server_name] = stdio
        self.writes[server_name] = write
        
        return session

    async def cleanup(self, server_name: str) -> None:
        """Clean up resources for a specific server.
        
        Properly cleans up all resources associated with a server connection,
        including the session, stdio transport, and write handler.
        
        Args:
            server_name: Name of the server to clean up
            
        Note:
            - Safe to call multiple times
            - Handles cleanup errors gracefully
            - Removes server from internal tracking
        """
        logger.debug("Cleaning up resources for server: %s", server_name)
        
        try:
            # Remove references to resources - actual cleanup is handled by AsyncExitStack
            if server_name in self.sessions:
                del self.sessions[server_name]
            
            if server_name in self.stdios:
                del self.stdios[server_name]
            
            if server_name in self.writes:
                del self.writes[server_name]
            
        except Exception as e:
            logger.error("Error during cleanup for %s: %s", server_name, str(e))
        finally:
            # Ensure all references are removed
            self.sessions.pop(server_name, None)
            self.stdios.pop(server_name, None)
            self.writes.pop(server_name, None)
            logger.debug("Cleanup completed for server: %s", server_name)

    async def cleanup_all(self) -> None:
        """Clean up all server resources.
        
        This method cleans up all resources for all connected servers.
        It ensures proper cleanup even in the presence of task cancellation.
        
        Note:
            - Safe to call multiple times
            - Handles cleanup errors gracefully
            - Cleans up all server resources
        """
        logger.debug("Starting cleanup of all servers")
        
        # Get list of servers to clean up
        servers = list(self.sessions.keys())
        
        try:
            # Clean up each server
            for server_name in servers:
                try:
                    await self.cleanup(server_name)
                except Exception as e:
                    logger.error("Error cleaning up server %s: %s", server_name, str(e))
            
            # Close the exit stack
            try:
                await self.exit_stack.aclose()
                logger.debug("Exit stack closed successfully")
            except asyncio.CancelledError:
                # Handle task cancellation gracefully
                logger.info("Task cancelled during exit stack cleanup")
                # Ensure the exit stack is closed even if cancelled
                await self.exit_stack.aclose()
            except Exception as e:
                logger.error("Error closing exit stack: %s", str(e))
                
        except Exception as e:
            logger.error("Error during cleanup_all: %s", str(e))
        finally:
            # Clear all remaining references
            self.sessions.clear()
            self.stdios.clear()
            self.writes.clear()
            logger.debug("All server resources cleaned up") 