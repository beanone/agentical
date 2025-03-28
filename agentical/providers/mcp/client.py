"""MCP client implementation."""

import asyncio
import json
import os
from typing import Dict, Any, AsyncIterator, Optional, Callable, Awaitable
from .models import (
    MCPConfig,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    MCPError,
    MCPErrorCode,
    MCPCapabilities,
    MCPProgress
)

ProgressCallback = Callable[[MCPProgress], Awaitable[None]]


class MCPConnection:
    """Manages a connection to an MCP server process."""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self._read_task: Optional[asyncio.Task] = None
        self._notification_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self._pending_requests: Dict[int, asyncio.Future] = {}
        
    async def connect(self):
        """Start the MCP server process and establish connection."""
        if self.process is not None:
            return
            
        # Prepare environment
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
            
        # Start process in working directory if specified
        cwd = self.config.workingDir if self.config.workingDir else None
            
        self.process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        
        # Start background task to read responses
        self._read_task = asyncio.create_task(self._read_responses())
        
    async def _read_responses(self):
        """Background task to read and handle server responses."""
        while self.process and not self.process.stdout.at_eof():
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                    
                message = json.loads(line)
                print(f"Received message: {message}")  # Debug print
                
                # Handle notifications
                if "method" in message and "id" not in message:
                    method = message["method"]
                    if method in self._notification_handlers:
                        print(f"Processing notification for method: {method}")  # Debug print
                        await self._notification_handlers[method](message["params"])
                # Handle responses
                elif "id" in message:
                    msg_id = message["id"]
                    if msg_id in self._pending_requests:
                        self._pending_requests[msg_id].set_result(message)
                        del self._pending_requests[msg_id]
                        
            except json.JSONDecodeError as e:
                print(f"Invalid JSON from server: {e}")
            except Exception as e:
                print(f"Error reading response: {e}")
                
    def register_notification_handler(
        self,
        method: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """Register a handler for notifications of a specific method."""
        self._notification_handlers[method] = handler
        
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server and get response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise MCPError(
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                "Not connected to MCP server"
            )
            
        # Create future for response
        if "id" in message:
            msg_id = message["id"]
            future = asyncio.Future()
            self._pending_requests[msg_id] = future
            
        # Send message
        msg_json = json.dumps(message)
        await self.process.stdin.write(msg_json.encode() + b"\n")
        await self.process.stdin.drain()
        
        # Wait for response if message has ID
        if "id" in message:
            try:
                response = await asyncio.wait_for(future, timeout=5.0)
                return response
            except asyncio.TimeoutError:
                del self._pending_requests[msg_id]
                raise MCPError(
                    MCPErrorCode.INTERNAL_ERROR,
                    "Timeout waiting for response"
                )
        return {}
        
    async def close(self):
        """Close the connection to the MCP server."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
                
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None


class MCPClient:
    """Client for interacting with an MCP server."""
    
    def __init__(
        self,
        server_id: str,
        config: MCPConfig,
        progress_callback: Optional[ProgressCallback] = None
    ):
        self.server_id = server_id
        self.connection = MCPConnection(config)
        self.capabilities: Optional[MCPCapabilities] = None
        self.progress_callback = progress_callback
        self._message_id = 0
        self._initialized = False
        
    def _next_message_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id
        
    async def _handle_progress(self, params: Dict[str, Any]):
        """Handle progress notification from server."""
        if self.progress_callback:
            progress = MCPProgress(**params)
            await self.progress_callback(progress)
            
    async def connect(self):
        """Connect and initialize the MCP server."""
        if self._initialized:
            return
            
        try:
            await self.connection.connect()
            
            # Register progress handler
            self.connection.register_notification_handler(
                "$/progress",
                self._handle_progress
            )
            
            # Send initialization request
            request = MCPRequest(
                id=self._next_message_id(),
                method="initialize",
                params={
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": True,
                        "progress": True,
                        "completion": False,
                        "sampling": False,
                        "cancellation": True
                    }
                }
            )
            
            response_data = await self.connection.send_message(request.model_dump())
            response = MCPResponse(**response_data)
            
            if response.error:
                raise MCPError(
                    response.error.code,
                    response.error.message,
                    response.error.data
                )
                
            if "capabilities" not in response.result:
                raise MCPError(
                    MCPErrorCode.INVALID_REQUEST,
                    "Server did not return capabilities in initialize response"
                )
                
            self.capabilities = MCPCapabilities(**response.result["capabilities"])
            self._initialized = True
        except Exception as e:
            # Ensure we clean up on initialization failure
            await self.close()
            if isinstance(e, MCPError):
                raise
            raise MCPError(
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                f"Failed to initialize server: {str(e)}"
            )
        
    async def execute(self, method: str, params: Dict[str, Any]) -> AsyncIterator[Any]:
        """Execute a method on the MCP server."""
        if not self._initialized:
            await self.initialize()
            
        request = MCPRequest(
            id=self._next_message_id(),
            method=method,
            params=params
        )
        
        try:
            response_data = await self.connection.send_message(request.model_dump())
            response = MCPResponse(**response_data)
            
            if response.error:
                raise MCPError(
                    response.error.code,
                    response.error.message,
                    response.error.data
                )
                
            yield response.result
            
        except Exception as e:
            if isinstance(e, MCPError):
                raise
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to execute method: {str(e)}"
            )
        
    async def cancel(self, request_id: int) -> None:
        """Cancel an ongoing request."""
        if not self._initialized:
            raise MCPError(
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                "Client not initialized"
            )
            
        if not self.capabilities or not self.capabilities.cancellation:
            raise MCPError(
                MCPErrorCode.INVALID_REQUEST,
                "Server does not support cancellation"
            )
            
        notification = MCPNotification(
            method="$/cancel",
            params={"id": request_id}
        )
        await self.connection.send_message(notification.model_dump())
        
    async def close(self):
        """Close the connection to the MCP server."""
        if self._initialized:
            try:
                # Send shutdown notification
                notification = MCPNotification(
                    method="shutdown",
                    params={}
                )
                await self.connection.send_message(notification.model_dump())
                
                # Send exit notification
                notification = MCPNotification(
                    method="exit",
                    params={}
                )
                await self.connection.send_message(notification.model_dump())
            except Exception:
                # Ignore errors during shutdown
                pass
            
        await self.connection.close()
        self.capabilities = None
        self._initialized = False

    async def _send_progress(self, progress: MCPProgress) -> None:
        """Send a progress notification to the server."""
        notification = MCPNotification(
            method="$/progress",
            params=progress.model_dump()
        )
        await self.connection.send_message(notification.model_dump())