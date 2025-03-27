"""Filesystem Tool for Agentical Framework.

This module provides a tool for filesystem operations.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from agentical.core.types import Tool, ToolParameter


class FSError(Exception):
    """Raised when there is an error performing a filesystem operation."""
    pass


def create_fs_tool() -> Tool:
    """Create a filesystem tool definition.
    
    Returns:
        Tool definition for filesystem operations
    """
    return Tool(
        name="filesystem",
        description="Perform basic filesystem operations",
        parameters={
            "operation": ToolParameter(
                type="string",
                description=(
                    "Operation to perform. Valid values: "
                    "'read' (read file contents), "
                    "'write' (write to file), "
                    "'list' (list directory contents)"
                ),
                required=True,
                enum=["read", "write", "list"]
            ),
            "path": ToolParameter(
                type="string", 
                description="Path to file or directory",
                required=True
            ),
            "content": ToolParameter(
                type="string",
                description="Content to write (only for write operation)",
                required=False
            )
        }
    )


async def collect_input() -> Dict[str, Any]:
    """Collect input parameters from user.
    
    Returns:
        Dictionary of parameters for the filesystem tool
        
    Raises:
        FSError: If input validation fails
    """
    # Get operation
    print("Available operations:")
    print("1. read - Read file contents")
    print("2. write - Write to file")
    print("3. list - List directory contents")
    
    operation = input("Enter operation: ").strip().lower()
    if operation not in ["read", "write", "list"]:
        raise FSError("Invalid operation")
        
    # Get path
    path = input("Enter path: ").strip()
    if not path:
        raise FSError("Path cannot be empty")
        
    # Get content for write operation
    content = None
    if operation == "write":
        content = input("Enter content to write: ")
        
    return {
        "operation": operation,
        "path": path,
        "content": content
    }


async def fs_handler(params: Dict[str, Any]) -> str:
    """Handle filesystem tool execution.
    
    Args:
        params: Dictionary containing:
            - operation: Operation to perform (read/write/list)
            - path: Path to file or directory
            - content: Content to write (only for write operation)
            
    Returns:
        Result of the operation
        
    Raises:
        FSError: If there is an error performing the operation
    """
    # Get parameters
    operation = params.get("operation")
    if not operation:
        raise FSError("Operation parameter is required")
        
    path = params.get("path")
    if not path:
        raise FSError("Path parameter is required")
        
    path = Path(path)
    
    try:
        # Handle read operation
        if operation == "read":
            if not path.is_file():
                raise FSError(f"File not found: {path}")
            with open(path, "r") as f:
                return f.read()
                
        # Handle write operation
        elif operation == "write":
            content = params.get("content")
            if not content:
                raise FSError("Content parameter is required for write operation")
                
            # Create parent directories if they don't exist
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
                
            with open(path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
            
        # Handle list operation
        elif operation == "list":
            if not path.exists():
                raise FSError(f"Path not found: {path}")
            if not path.is_dir():
                raise FSError(f"Not a directory: {path}")
                
            contents = []
            for item in path.iterdir():
                item_type = "dir" if item.is_dir() else "file"
                contents.append(f"{item.name} ({item_type})")
                
            return "\n".join(contents) if contents else "Directory is empty"
            
        else:
            raise FSError(f"Invalid operation: {operation}")
            
    except FSError:
        raise
    except Exception as e:
        raise FSError(f"Error performing operation: {str(e)}") 