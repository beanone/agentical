"""Unit tests for terminal_server.py.

This module provides test coverage for the terminal server implementation.
"""

import pytest
from unittest.mock import patch, MagicMock
from server.terminal_server import run_command, WORKSPACE_DIR


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing."""
    with patch('server.terminal_server.subprocess.run') as mock_run:
        # Set up default mock response
        mock_process = MagicMock()
        mock_process.stdout = "Command output"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        yield mock_run


@pytest.mark.asyncio
class TestRunCommand:
    """Test cases for run_command function."""

    async def test_successful_command(self, mock_subprocess):
        """Test running a successful command."""
        mock_subprocess.return_value.stdout = "Hello World"
        mock_subprocess.return_value.stderr = ""

        result = await run_command("echo Hello World")

        mock_subprocess.assert_called_once_with(
            "echo Hello World",
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            check=False
        )
        assert result == "Hello World"

    async def test_command_with_stderr(self, mock_subprocess):
        """Test command that writes to stderr."""
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error message"

        result = await run_command("invalid_command")

        assert result == "Error message"

    async def test_command_with_exception(self, mock_subprocess):
        """Test command that raises an exception."""
        mock_subprocess.side_effect = Exception("Command failed")

        result = await run_command("problematic_command")

        assert result == "Command failed"

    async def test_workspace_directory(self, mock_subprocess):
        """Test that commands run in the correct workspace directory."""
        await run_command("ls")

        mock_subprocess.assert_called_once_with(
            "ls",
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            check=False
        )

    async def test_command_output_priority(self, mock_subprocess):
        """Test that stdout is preferred over stderr when both are present."""
        mock_subprocess.return_value.stdout = "Standard output"
        mock_subprocess.return_value.stderr = "Error output"

        result = await run_command("mixed_output_command")

        assert result == "Standard output"