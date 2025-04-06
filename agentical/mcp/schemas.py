"""Configuration schemas for MCP provider."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator

class ServerConfig(BaseModel):
    """Schema for individual server configuration."""
    command: str = Field(..., description="Command to start the server")
    args: List[str] = Field(default_factory=list, description="Arguments for the server command")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables for the server")
    
    @field_validator('command')
    def command_not_empty(cls, v: str) -> str:
        """Validate that command is not empty."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v
    
    @field_validator('args')
    def validate_args(cls, v: List[str], values: Dict[str, Any]) -> List[str]:
        """Validate args list contains valid strings when present."""
        if v and any(not isinstance(arg, str) or not arg.strip() for arg in v):
            raise ValueError("All args must be non-empty strings")
        return v

class MCPConfig(BaseModel):
    """Schema for MCP configuration file."""
    servers: Dict[str, ServerConfig] = Field(
        ...,
        description="Dictionary of server configurations keyed by server name"
    )
    
    @field_validator('servers')
    def servers_not_empty(cls, v: Dict[str, ServerConfig]) -> Dict[str, ServerConfig]:
        """Validate that servers dictionary is not empty."""
        if not v:
            raise ValueError("At least one server configuration must be provided")
        if any(not name.strip() for name in v.keys()):
            raise ValueError("Server names cannot be empty")
        return v 