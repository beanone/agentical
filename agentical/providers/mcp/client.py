"""MCP client implementation."""

import asyncio
import json
import os
import logging
import contextvars
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

class RequestIdFilter(logging.Filter):
    """Adds request ID to log records when available."""
    
    def filter(self, record):
        request_id = _request_ctx.get()
        if request_id is not None:
            record.request_id = f"[request.{request_id}]"
        else:
            record.request_id = ""
        return True

# Configure module logger with a consistent format
logger = logging.getLogger(__name__)
request_filter = RequestIdFilter()
logger.addFilter(request_filter)

# Request context for tracking request IDs in logs
_request_ctx = contextvars.ContextVar('request_id', default=None)

class RequestContext:
    """Context manager for tracking request IDs in logs."""
    
    def __init__(self, request_id: int):
        self.request_id = request_id
        self.token = None
        
    def __enter__(self):
        self.token = _request_ctx.set(self.request_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        _request_ctx.reset(self.token)

def get_request_context() -> Optional[int]:
    """Get the current request ID from context if available."""
    return _request_ctx.get()

class MCPConnection:
    """Manages a connection to an MCP server process."""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self._read_task: Optional[asyncio.Task] = None
        self._notification_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._logger = logging.getLogger(f"{__name__}.MCPConnection")
        
    async def connect(self):
        """Start the MCP server process and establish connection."""
        if self.process is not None:
            self._logger.debug("[lifecycle.application.state] Server already running")
            return
            
        self._logger.info("[lifecycle.application] Starting: Launching MCP server process")
        
        # Prepare environment
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
            
        # Start process in working directory if specified
        cwd = self.config.workingDir if self.config.workingDir else None
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd
            )
            self._logger.info("[lifecycle.application] Running: MCP server process started successfully")
            
            # Start background task to read responses
            self._read_task = asyncio.create_task(self._read_responses())
            
        except Exception as e:
            self._logger.error("[lifecycle.application] Failed: Could not start MCP server - %s", str(e))
            raise
        
    async def _read_responses(self):
        """Background task to read and handle server responses."""
        self._logger.debug("[flow.internal] Starting response reader loop")
        try:
            while self.process and not await self.process.stdout.at_eof():
                try:
                    # Read errors are fatal - they mean the connection is broken
                    line = await self.process.stdout.readline()
                    if not line:
                        self._logger.info("[lifecycle.application] Shutdown: Server closed connection")
                        # EOF reached - fail any pending requests with timeout
                        for future in self._pending_requests.values():
                            if not future.done():
                                future.set_exception(MCPError(
                                    MCPErrorCode.INTERNAL_ERROR,
                                    "Timeout waiting for response"
                                ))
                        self._pending_requests.clear()
                        break
                    
                    try:
                        message = json.loads(line)
                        self._logger.debug("[flow.message] Received: %s", message)
                        
                        # Handle notifications
                        if "method" in message and "id" not in message:
                            method = message["method"]
                            if method in self._notification_handlers:
                                self._logger.debug("[flow.notification] Processing: %s", method)
                                await self._notification_handlers[method](message["params"])
                            else:
                                self._logger.warning("[protocol.message] Unknown: Unrecognized notification method %s", method)
                        # Handle responses
                        elif "id" in message:
                            msg_id = message["id"]
                            with RequestContext(msg_id):
                                if msg_id in self._pending_requests:
                                    self._logger.debug("[flow.response] Completed: Request %s", msg_id)
                                    self._pending_requests[msg_id].set_result(message)
                                    del self._pending_requests[msg_id]
                                else:
                                    self._logger.warning("[protocol.message] Unknown: Response for unknown request %s", msg_id)
                            
                    except json.JSONDecodeError as e:
                        # JSON decode errors only affect the current message
                        error_msg = f"Invalid JSON from server: {e}. Raw message: {line!r}"
                        self._logger.warning("[protocol.message] Invalid: JSON decode error - %s", str(e))
                        
                        # If there's only one pending request, it was likely waiting for this response
                        if len(self._pending_requests) == 1:
                            msg_id, future = next(iter(self._pending_requests.items()))
                            with RequestContext(msg_id):
                                self._logger.warning("[protocol.message] Failed: Request %s failed due to invalid JSON", msg_id)
                                future.set_exception(MCPError(MCPErrorCode.INTERNAL_ERROR, error_msg))
                                del self._pending_requests[msg_id]
                        
                except Exception as e:
                    # Any other error (especially read errors) means the connection is dead
                    error_msg = f"Fatal connection error: {str(e)}"
                    self._logger.error("[lifecycle.application] Failed: Fatal IO error - %s", str(e))
                    
                    # Fail all pending requests and stop reading
                    for future in self._pending_requests.values():
                        if not future.done():
                            future.set_exception(MCPError(MCPErrorCode.INTERNAL_ERROR, error_msg))
                    self._pending_requests.clear()
                    return
                
        finally:
            self._logger.debug("[flow.internal] Response reader loop ended")
            # Connection is closed, fail any remaining requests
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(MCPError(MCPErrorCode.INTERNAL_ERROR, "Timeout waiting for response"))
            self._pending_requests.clear()
        
    def register_notification_handler(
        self,
        method: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """Register a handler for notifications of a specific method."""
        self._logger.debug("[flow.internal] Registered handler for notification method: %s", method)
        self._notification_handlers[method] = handler
        
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server and get response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            self._logger.error("[lifecycle.application] Failed: Server not running")
            raise MCPError(
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                "Not connected to MCP server"
            )
            
        # Create future for response
        if "id" in message:
            msg_id = message["id"]
            with RequestContext(msg_id):
                self._logger.debug("[flow.message] Sending: Request %s", msg_id)
                future = asyncio.Future()
                self._pending_requests[msg_id] = future
        else:
            self._logger.debug("[flow.message] Sending: Notification %s", message.get("method", "unknown"))
            
        # Send message
        msg_json = json.dumps(message)
        await self.process.stdin.write(msg_json.encode() + b"\n")
        await self.process.stdin.drain()
        
        # Wait for response if message has ID
        if "id" in message:
            msg_id = message["id"]
            with RequestContext(msg_id):
                try:
                    self._logger.debug("[flow.request] Processing: Waiting for response to %s", msg_id)
                    response = await asyncio.wait_for(future, timeout=5.0)
                    self._logger.debug("[flow.response] Completed: Request %s", msg_id)
                    return response
                except asyncio.TimeoutError:
                    self._logger.warning("[protocol.message] Timeout: Request %s timed out waiting for response", msg_id)
                    del self._pending_requests[msg_id]
                    raise MCPError(
                        MCPErrorCode.INTERNAL_ERROR,
                        "Timeout waiting for response"
                    )
        return {}
        
    async def close(self):
        """Close the connection to the MCP server."""
        self._logger.info("[lifecycle.application] Shutdown: Initiating server shutdown")
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
                self._logger.warning("[lifecycle.application] Shutdown: Server not responding, forcing termination")
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
                self._logger.info("[lifecycle.application] Shutdown: Server shutdown completed successfully")


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
        self._logger = logging.getLogger(f"{__name__}.MCPClient")
        
    def _next_message_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id
        
    async def _handle_progress(self, params: Dict[str, Any]):
        """Handle progress notification from server."""
        if self.progress_callback:
            self._logger.debug("[flow.progress] Processing: Progress update received")
            progress = MCPProgress(**params)
            await self.progress_callback(progress)
            
    async def connect(self):
        """Connect and initialize the MCP server."""
        if self._initialized:
            self._logger.debug("[lifecycle.client.state] Client already initialized")
            return
            
        self._logger.info("[lifecycle.client] Starting: Initializing client for server %s", self.server_id)
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
                self._logger.error("[lifecycle.client] Failed: Initialization failed - %s", response.error)
                raise MCPError(
                    response.error.code,
                    response.error.message,
                    response.error.data
                )
                
            if "capabilities" not in response.result:
                self._logger.error("[lifecycle.client] Failed: Server did not return capabilities")
                raise MCPError(
                    MCPErrorCode.INVALID_REQUEST,
                    "Server did not return capabilities in initialize response"
                )
                
            self.capabilities = MCPCapabilities(**response.result["capabilities"])
            self._initialized = True
            self._logger.info("[lifecycle.client] Ready: Client initialized successfully")
            
        except Exception as e:
            self._logger.error("[lifecycle.client] Failed: Client initialization failed - %s", str(e))
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
            await self.connect()  # Restore automatic initialization
            
        self._logger.info("[lifecycle.request] Starting: Executing method %s", method)
        request = MCPRequest(
            id=self._next_message_id(),
            method=method,
            params=params
        )
        
        try:
            response_data = await self.connection.send_message(request.model_dump())
            response = MCPResponse(**response_data)
            
            if response.error:
                self._logger.error("[lifecycle.request] Failed: Method %s failed - %s", method, response.error)
                raise MCPError(
                    response.error.code,
                    response.error.message,
                    response.error.data
                )
                
            self._logger.info("[lifecycle.request] Completed: Method %s completed successfully", method)
            yield response.result
            
        except Exception as e:
            self._logger.error("[lifecycle.request] Failed: Method %s execution failed - %s", method, str(e))
            if isinstance(e, MCPError):
                raise
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Method execution failed: {str(e)}"
            )
        
    async def cancel(self, request_id: int):
        """Cancel an ongoing request."""
        if not self._initialized:
            self._logger.error("[lifecycle.client] Failed: Client not initialized")
            raise MCPError(
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                "Client not initialized"
            )
            
        if not self.capabilities or not self.capabilities.cancellation:
            self._logger.error("[lifecycle.request] Failed: Server does not support request cancellation")
            raise MCPError(
                MCPErrorCode.INVALID_REQUEST,
                "Server does not support request cancellation"
            )
            
        self._logger.info("[lifecycle.request] Cancelled: Request %s cancelled by user", request_id)
        notification = MCPNotification(
            method="$/cancel",
            params={"id": request_id}
        )
        await self.connection.send_message(notification.model_dump())
        
    async def close(self):
        """Close the connection to the MCP server."""
        if self._initialized:
            self._logger.info("[lifecycle.client] Shutdown: Initiating client shutdown for server %s", self.server_id)
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
        self._logger.info("[lifecycle.client] Shutdown: Client shutdown completed successfully")