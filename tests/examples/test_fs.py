"""Tests for the filesystem tool."""

import os
import pytest
from pathlib import Path
from typing import Dict, Any, Generator

from examples.tools.fs_tool import (
    FSError,
    create_fs_tool,
    fs_handler
)


@pytest.fixture
def test_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    # Create test files and directories
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    test_subdir = tmp_path / "subdir"
    test_subdir.mkdir()
    
    test_subfile = test_subdir / "subfile.txt"
    test_subfile.write_text("Subfile content")
    
    yield tmp_path


def test_create_fs_tool() -> None:
    """Test creating the filesystem tool definition."""
    tool = create_fs_tool()
    
    # Verify tool properties
    assert tool.name == "filesystem"
    assert "filesystem operations" in tool.description.lower()
    
    # Verify parameters
    params = tool.parameters
    assert "operation" in params
    assert "path" in params
    assert "content" in params
    
    # Verify operation parameter
    assert params["operation"].type == "string"
    assert params["operation"].required is True
    assert set(params["operation"].enum) == {"read", "write", "list"}
    
    # Verify path parameter
    assert params["path"].type == "string"
    assert params["path"].required is True
    
    # Verify content parameter
    assert params["content"].type == "string"
    assert params["content"].required is False


@pytest.mark.asyncio
async def test_fs_handler_read(test_dir: Path) -> None:
    """Test reading files with the filesystem handler."""
    # Test reading existing file
    result1 = await fs_handler({
        "operation": "read",
        "path": str(test_dir / "test.txt")
    })
    assert result1 == "Test content"
    
    # Test reading file in subdirectory
    result2 = await fs_handler({
        "operation": "read",
        "path": str(test_dir / "subdir" / "subfile.txt")
    })
    assert result2 == "Subfile content"
    
    # Test reading nonexistent file
    with pytest.raises(FSError, match="File not found"):
        await fs_handler({
            "operation": "read",
            "path": str(test_dir / "nonexistent.txt")
        })


@pytest.mark.asyncio
async def test_fs_handler_write(test_dir: Path) -> None:
    """Test writing files with the filesystem handler."""
    # Test writing new file
    new_file = test_dir / "new.txt"
    result1 = await fs_handler({
        "operation": "write",
        "path": str(new_file),
        "content": "New content"
    })
    assert "Successfully wrote" in result1
    assert new_file.read_text() == "New content"
    
    # Test writing to existing file
    result2 = await fs_handler({
        "operation": "write",
        "path": str(test_dir / "test.txt"),
        "content": "Updated content"
    })
    assert "Successfully wrote" in result2
    assert (test_dir / "test.txt").read_text() == "Updated content"
    
    # Test writing without content
    with pytest.raises(FSError, match="Content parameter is required"):
        await fs_handler({
            "operation": "write",
            "path": str(test_dir / "error.txt")
        })


@pytest.mark.asyncio
async def test_fs_handler_list(test_dir: Path) -> None:
    """Test listing directory contents with the filesystem handler."""
    # Test listing root directory
    result1 = await fs_handler({
        "operation": "list",
        "path": str(test_dir)
    })
    assert "test.txt (file)" in result1
    assert "subdir (dir)" in result1
    
    # Test listing subdirectory
    result2 = await fs_handler({
        "operation": "list",
        "path": str(test_dir / "subdir")
    })
    assert "subfile.txt (file)" in result2
    
    # Test listing empty directory
    empty_dir = test_dir / "empty"
    empty_dir.mkdir()
    result3 = await fs_handler({
        "operation": "list",
        "path": str(empty_dir)
    })
    assert result3 == "Directory is empty"
    
    # Test listing nonexistent directory
    with pytest.raises(FSError, match="Path not found"):
        await fs_handler({
            "operation": "list",
            "path": str(test_dir / "nonexistent")
        })


@pytest.mark.asyncio
async def test_fs_handler_invalid_operations() -> None:
    """Test filesystem handler with invalid operations."""
    # Test missing operation
    with pytest.raises(FSError, match="Operation parameter is required"):
        await fs_handler({})
    
    # Test invalid operation
    with pytest.raises(FSError, match="Invalid operation"):
        await fs_handler({
            "operation": "invalid",
            "path": "test.txt"
        })
    
    # Test missing path
    with pytest.raises(FSError, match="Path parameter is required"):
        await fs_handler({
            "operation": "read"
        }) 