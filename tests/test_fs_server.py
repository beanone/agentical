"""Unit tests for fs_server.py.

This module provides comprehensive test coverage for the filesystem server implementation.
"""

import os
import pytest
from pathlib import Path
from server.fs_server import read_file, write_file, list_directory, FSError, WORKSPACE_DIR


@pytest.fixture
async def setup_workspace():
    """Set up a temporary workspace for testing."""
    # Create workspace directory if it doesn't exist
    workspace = Path(WORKSPACE_DIR)
    workspace.mkdir(parents=True, exist_ok=True)

    # Create some test files and directories
    test_dir = workspace / "test_dir"
    test_dir.mkdir(exist_ok=True)

    test_file = workspace / "test.txt"
    test_file.write_text("Hello, World!")

    nested_dir = test_dir / "nested"
    nested_dir.mkdir(exist_ok=True)

    nested_file = nested_dir / "nested.txt"
    nested_file.write_text("Nested content")

    yield

    # Cleanup after tests
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    test_file.unlink(missing_ok=True)


@pytest.mark.asyncio
class TestReadFile:
    """Test cases for read_file function."""

    async def test_read_existing_file(self, setup_workspace):
        """Test reading an existing file."""
        content = await read_file("test.txt")
        assert content == "Hello, World!"

    async def test_read_nested_file(self, setup_workspace):
        """Test reading a file in a nested directory."""
        content = await read_file("test_dir/nested/nested.txt")
        assert content == "Nested content"

    async def test_read_nonexistent_file(self, setup_workspace):
        """Test reading a non-existent file."""
        result = await read_file("nonexistent.txt")
        assert "File not found" in result

    async def test_read_directory_as_file(self, setup_workspace):
        """Test attempting to read a directory as a file."""
        result = await read_file("test_dir")
        assert "File not found" in result

    async def test_read_file_outside_workspace(self, setup_workspace):
        """Test attempting to read a file outside the workspace."""
        result = await read_file("../outside.txt")
        assert "File not found" in result


@pytest.mark.asyncio
class TestWriteFile:
    """Test cases for write_file function."""

    async def test_write_new_file(self, setup_workspace):
        """Test writing to a new file."""
        result = await write_file("new_file.txt", "New content")
        assert "Successfully wrote" in result

        # Verify the content was written
        content = await read_file("new_file.txt")
        assert content == "New content"

    async def test_write_existing_file(self, setup_workspace):
        """Test overwriting an existing file."""
        result = await write_file("test.txt", "Updated content")
        assert "Successfully wrote" in result

        # Verify the content was updated
        content = await read_file("test.txt")
        assert content == "Updated content"

    async def test_write_nested_file(self, setup_workspace):
        """Test writing to a file in a nested directory."""
        result = await write_file("test_dir/nested/new_nested.txt", "New nested content")
        assert "Successfully wrote" in result

        # Verify the content was written
        content = await read_file("test_dir/nested/new_nested.txt")
        assert content == "New nested content"

    async def test_write_file_create_dirs(self, setup_workspace):
        """Test writing to a file in a new directory structure."""
        result = await write_file("new_dir/sub_dir/file.txt", "Content in new dirs")
        assert "Successfully wrote" in result

        # Verify the content was written
        content = await read_file("new_dir/sub_dir/file.txt")
        assert content == "Content in new dirs"

    async def test_write_file_invalid_path(self, setup_workspace):
        """Test writing to an invalid path."""
        result = await write_file("", "Some content")
        assert isinstance(result, str)  # Should return error message


@pytest.mark.asyncio
class TestListDirectory:
    """Test cases for list_directory function."""

    async def test_list_root_directory(self, setup_workspace):
        """Test listing the root directory."""
        result = await list_directory(".")
        assert "test.txt (file)" in result
        assert "test_dir (dir)" in result

    async def test_list_nested_directory(self, setup_workspace):
        """Test listing a nested directory."""
        result = await list_directory("test_dir/nested")
        assert "nested.txt (file)" in result

    async def test_list_empty_directory(self, setup_workspace):
        """Test listing an empty directory."""
        # Create an empty directory
        empty_dir = Path(WORKSPACE_DIR) / "empty_dir"
        empty_dir.mkdir(exist_ok=True)

        result = await list_directory("empty_dir")
        assert result == "Directory is empty"

        # Cleanup
        empty_dir.rmdir()

    async def test_list_nonexistent_directory(self, setup_workspace):
        """Test listing a non-existent directory."""
        result = await list_directory("nonexistent_dir")
        assert "Path not found" in result

    async def test_list_file_as_directory(self, setup_workspace):
        """Test attempting to list a file as a directory."""
        result = await list_directory("test.txt")
        assert "Not a directory" in result