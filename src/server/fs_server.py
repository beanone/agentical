"""Filesystem Tool for Agentical Framework.

This module provides MCP-compliant tools for filesystem operations.
"""

import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem")
DEFAULT_WORKSPACE = os.path.expanduser("~/mcp/workspace")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", DEFAULT_WORKSPACE)

class FSError(Exception):
    """Raised when there is an error performing a filesystem operation."""
    pass

@mcp.tool()
async def read_file(path: str) -> str:
    """Read contents of a file.
    
    Args:
        path: Path to the file to read
        
    Returns:
        Contents of the file as a string
        
    Raises:
        FSError: If file cannot be read
    """
    try:
        file_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not file_path.is_file():
            raise FSError(f"File not found: {path}")
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return str(e)

@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Success message
        
    Raises:
        FSError: If file cannot be written
    """
    try:
        file_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)
        with open(file_path, "w") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return str(e)

@mcp.tool()
async def list_directory(path: str = ".") -> str:
    """List contents of a directory.
    
    Args:
        path: Path to the directory to list (defaults to current directory)
        
    Returns:
        Directory listing as a string
        
    Raises:
        FSError: If directory cannot be listed
    """
    try:
        dir_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not dir_path.exists():
            raise FSError(f"Path not found: {path}")
        if not dir_path.is_dir():
            raise FSError(f"Not a directory: {path}")
            
        contents = []
        for item in dir_path.iterdir():
            item_type = "dir" if item.is_dir() else "file"
            contents.append(f"{item.name} ({item_type})")
            
        return "\n".join(contents) if contents else "Directory is empty"
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    mcp.run(transport='stdio') 