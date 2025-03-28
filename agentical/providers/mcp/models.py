"""Data models for MCP implementation."""

from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, model_validator


class MCPErrorCode:
    """Standard MCP error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_NOT_INITIALIZED = -32002
    INVALID_REQUEST_SEQUENCE = -32003


class MCPError(Exception):
    """MCP protocol error."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


class MCPCapabilities(BaseModel):
    """MCP Server capabilities."""
    tools: bool = True
    progress: bool = True
    completion: bool = False
    sampling: bool = False
    cancellation: bool = True


class MCPErrorDetail(BaseModel):
    """JSON-RPC 2.0 error detail."""
    code: int
    message: str
    data: Optional[Any] = None


class MCPRequest(BaseModel):
    """JSON-RPC 2.0 request message."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)  # Default to empty dict


class MCPResponse(BaseModel):
    """JSON-RPC 2.0 response message."""
    jsonrpc: str = "2.0"
    id: Optional[int]
    result: Optional[Any] = None
    error: Optional[MCPErrorDetail] = None


class MCPNotification(BaseModel):
    """JSON-RPC 2.0 notification message."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)  # Default to empty dict


class MCPMessage(BaseModel):
    """Union type for all MCP messages."""
    content: Union[MCPRequest, MCPResponse, MCPNotification]


class MCPConfig(BaseModel):
    """Configuration for MCP servers."""
    command: str
    args: list[str]
    config: Optional[Dict[str, Any]] = None
    workingDir: Optional[str] = None
    env: Optional[Dict[str, str]] = None


class MCPServerConfig(BaseModel):
    """Root configuration for all MCP servers."""
    mcpServers: Dict[str, MCPConfig]

    @model_validator(mode='after')
    def validate_servers(self) -> 'MCPServerConfig':
        """Validate that there is at least one server configured."""
        if not self.mcpServers:
            raise ValueError("At least one MCP server must be configured")
        return self


class MCPProgress(BaseModel):
    """Progress notification from MCP server."""
    operation_id: str
    progress: float = Field(ge=0.0, le=1.0)
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    is_final: bool = False  # Indicates if this is the final progress update