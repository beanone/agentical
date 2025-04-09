"""Unit tests for chat_client.py."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agentical import chat_client
from agentical.api import LLMBackend
from agentical.mcp.config import MCPConfigProvider


class MockProvider:
    """Mock provider class that includes async context manager methods."""

    def __init__(self):
        self.initialize = AsyncMock()
        self.cleanup = AsyncMock()
        self.mcp_connect = AsyncMock()
        self.mcp_connect_all = AsyncMock()
        self.chat_loop = AsyncMock()
        self.process_query = AsyncMock(return_value="Test response")
        self.list_available_servers = Mock(return_value=["server1", "server2"])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_provider():
    """Create a mock MCPToolProvider."""
    return MockProvider()


@pytest.fixture
def mock_llm_backend():
    """Fixture providing a mock LLM backend."""
    return Mock(spec=LLMBackend)


@pytest.fixture
def mock_config_provider():
    """Fixture providing a mock config provider."""
    provider = Mock(spec=MCPConfigProvider)
    provider.load_config = AsyncMock(return_value={})
    return provider


@pytest.fixture
def mock_config_file(tmp_path):
    """Fixture providing a temporary config file."""
    config_file = tmp_path / "test_config.json"
    config_file.write_text("{}")
    return str(config_file)


def test_parse_arguments_default():
    """Test parse_arguments with default values."""
    with patch("sys.argv", ["script.py"]):
        args = chat_client.parse_arguments()
        assert args.config == "config.json"


def test_parse_arguments_custom():
    """Test parse_arguments with custom config path."""
    with patch("sys.argv", ["script.py", "--config", "custom_config.json"]):
        args = chat_client.parse_arguments()
        assert args.config == "custom_config.json"


@pytest.mark.asyncio
async def test_interactive_server_selection_valid_choice(mock_provider):
    """Test interactive_server_selection with valid server choice."""
    with patch("builtins.input", return_value="1"):
        with patch("builtins.print"):
            result = await chat_client.interactive_server_selection(mock_provider)
            assert result == "server1"


@pytest.mark.asyncio
async def test_interactive_server_selection_all_servers(mock_provider):
    """Test interactive_server_selection with 'all servers' choice."""
    with patch("builtins.input", return_value="3"):  # 3 is all servers (2 servers + 1)
        with patch("builtins.print"):
            result = await chat_client.interactive_server_selection(mock_provider)
            assert result is None


@pytest.mark.asyncio
async def test_interactive_server_selection_invalid_then_valid(mock_provider):
    """Test interactive_server_selection with invalid input followed by valid input."""
    input_values = ["invalid", "0", "1"]  # First two invalid, then valid
    input_mock = MagicMock(side_effect=input_values)

    with patch("builtins.input", input_mock):
        with patch("builtins.print"):
            result = await chat_client.interactive_server_selection(mock_provider)
            assert result == "server1"
            assert input_mock.call_count == 3


@pytest.mark.asyncio
async def test_chat_loop_quit(mock_provider):
    """Test chat_loop with quit command."""
    with patch("builtins.input", return_value="quit"):
        with patch("builtins.print"):
            await chat_client.chat_loop(mock_provider)
            mock_provider.process_query.assert_not_called()


@pytest.mark.asyncio
async def test_chat_loop_process_query(mock_provider):
    """Test chat_loop processing a query before quitting."""
    input_values = ["test query", "quit"]

    with patch("builtins.input", side_effect=input_values):
        with patch("builtins.print"):
            await chat_client.chat_loop(mock_provider)
            mock_provider.process_query.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_chat_loop_error_handling(mock_provider):
    """Test chat_loop error handling during query processing."""
    mock_provider.process_query.side_effect = Exception("Test error")
    input_values = ["test query", "quit"]

    with patch("builtins.input", side_effect=input_values):
        with patch("builtins.print"):
            await chat_client.chat_loop(mock_provider)
            mock_provider.process_query.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_run_demo_single_server(mock_llm_backend, mock_config_provider):
    """Test running demo with single server selection."""
    # Setup mock provider
    provider = MockProvider()

    # Create a print function that only patches specific prints
    original_print = print

    def selective_print(*args, **kwargs):
        if args and isinstance(args[0], str) and args[0].startswith("\nQuery:"):
            return  # Skip printing queries
        original_print(*args, **kwargs)

    # Mock user input for server selection and chat loop
    input_values = ["1", "quit"]  # First for server selection, second for chat loop
    input_mock = MagicMock(side_effect=input_values)

    # Mock user input for server selection and sys.argv
    with (
        patch("builtins.input", input_mock),
        patch("builtins.print", selective_print),
        patch("agentical.chat_client.MCPToolProvider", return_value=provider),
    ):
        # Run demo
        await chat_client.run_demo(
            mock_llm_backend, config_provider=mock_config_provider
        )

        # Verify provider interactions
        provider.initialize.assert_called_once()
        provider.mcp_connect.assert_called_once_with("server1")
        provider.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_demo_all_servers(mock_llm_backend, mock_config_provider):
    """Test running demo with all servers selection."""
    # Setup mock provider
    provider = MockProvider()

    # Create a print function that only patches specific prints
    original_print = print

    def selective_print(*args, **kwargs):
        if args and isinstance(args[0], str) and args[0].startswith("\nQuery:"):
            return  # Skip printing queries
        original_print(*args, **kwargs)

    # Mock user input for server selection and chat loop
    input_values = ["3", "quit"]  # 3 for all servers, quit for chat loop
    input_mock = MagicMock(side_effect=input_values)

    # Mock user input for server selection and sys.argv
    with (
        patch("builtins.input", input_mock),
        patch("builtins.print", selective_print),
        patch("agentical.chat_client.MCPToolProvider", return_value=provider),
    ):
        # Run demo
        await chat_client.run_demo(
            mock_llm_backend, config_provider=mock_config_provider
        )

        # Verify provider interactions
        provider.initialize.assert_called_once()
        provider.mcp_connect_all.assert_called_once()
        provider.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_demo_all_servers_connection_failure(
    mock_llm_backend, mock_config_provider
):
    """Test handling of connection failure when connecting to all servers."""
    # Setup mock provider with connection failure
    provider = MockProvider()
    provider.mcp_connect_all.side_effect = Exception("Connection failed")

    # Create a print function that only patches specific prints
    original_print = print

    def selective_print(*args, **kwargs):
        if args and isinstance(args[0], str) and args[0].startswith("\nQuery:"):
            return  # Skip printing queries
        original_print(*args, **kwargs)

    # Mock user input for server selection and chat loop
    input_values = ["3", "quit"]  # 3 for all servers, quit for chat loop
    input_mock = MagicMock(side_effect=input_values)

    # Mock user input for server selection and sys.argv
    with (
        patch("builtins.input", input_mock),
        patch("builtins.print", selective_print),
        patch("agentical.chat_client.MCPToolProvider", return_value=provider),
    ):
        # Run demo and expect exception
        with pytest.raises(Exception, match="Connection failed"):
            await chat_client.run_demo(
                mock_llm_backend, config_provider=mock_config_provider
            )

        # Verify provider interactions
        provider.initialize.assert_called_once()
        provider.mcp_connect_all.assert_called_once()
        provider.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_demo_missing_config(mock_llm_backend, tmp_path):
    """Test handling of missing configuration file."""
    nonexistent_config = str(tmp_path / "nonexistent.json")

    with (
        patch("sys.argv", ["script.py", "--config", nonexistent_config]),
        patch("builtins.print"),
        pytest.raises(SystemExit, match="1"),
    ):
        await chat_client.run_demo(mock_llm_backend, config_provider=None)
