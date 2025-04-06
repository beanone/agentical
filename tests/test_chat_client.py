"""Unit tests for chat_client.py."""

import pytest
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from agentical.chat_client import (
    parse_arguments,
    interactive_server_selection,
    chat_loop,
    run_demo
)
from agentical.mcp import MCPToolProvider
from agentical.api import LLMBackend
from agentical.mcp.config import FileBasedMCPConfigProvider

@pytest.fixture
def mock_provider():
    """Create a mock MCPToolProvider."""
    provider = AsyncMock(spec=MCPToolProvider)
    provider.list_available_servers.return_value = ["server1", "server2"]
    provider.process_query = AsyncMock(return_value="Test response")
    provider.cleanup = AsyncMock()
    return provider

@pytest.fixture
def mock_llm_backend():
    """Create a mock LLMBackend."""
    return AsyncMock(spec=LLMBackend)

def test_parse_arguments_default():
    """Test parse_arguments with default values."""
    with patch('sys.argv', ['script.py']):
        args = parse_arguments()
        assert args.config == "config.json"

def test_parse_arguments_custom():
    """Test parse_arguments with custom config path."""
    with patch('sys.argv', ['script.py', '--config', 'custom_config.json']):
        args = parse_arguments()
        assert args.config == "custom_config.json"

@pytest.mark.asyncio
async def test_interactive_server_selection_valid_choice(mock_provider):
    """Test interactive_server_selection with valid server choice."""
    with patch('builtins.input', return_value="1"):
        with patch('builtins.print'):
            result = await interactive_server_selection(mock_provider)
            assert result == "server1"

@pytest.mark.asyncio
async def test_interactive_server_selection_all_servers(mock_provider):
    """Test interactive_server_selection with 'all servers' choice."""
    with patch('builtins.input', return_value="3"):  # 3 is all servers (2 servers + 1)
        with patch('builtins.print'):
            result = await interactive_server_selection(mock_provider)
            assert result is None

@pytest.mark.asyncio
async def test_interactive_server_selection_invalid_then_valid(mock_provider):
    """Test interactive_server_selection with invalid input followed by valid input."""
    input_values = ["invalid", "0", "1"]  # First two invalid, then valid
    input_mock = MagicMock(side_effect=input_values)
    
    with patch('builtins.input', input_mock):
        with patch('builtins.print'):
            result = await interactive_server_selection(mock_provider)
            assert result == "server1"
            assert input_mock.call_count == 3

@pytest.mark.asyncio
async def test_chat_loop_quit(mock_provider):
    """Test chat_loop with quit command."""
    with patch('builtins.input', return_value="quit"):
        with patch('builtins.print'):
            await chat_loop(mock_provider)
            mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_chat_loop_process_query(mock_provider):
    """Test chat_loop processing a query before quitting."""
    input_values = ["test query", "quit"]
    
    with patch('builtins.input', side_effect=input_values):
        with patch('builtins.print'):
            await chat_loop(mock_provider)
            
            mock_provider.process_query.assert_called_once_with("test query")
            mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_chat_loop_error_handling(mock_provider):
    """Test chat_loop error handling during query processing."""
    mock_provider.process_query.side_effect = Exception("Test error")
    input_values = ["test query", "quit"]
    
    with patch('builtins.input', side_effect=input_values):
        with patch('builtins.print'):
            await chat_loop(mock_provider)
            
            mock_provider.process_query.assert_called_once_with("test query")
            mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_run_demo_config_not_found(mock_llm_backend):
    """Test run_demo with non-existent config file."""
    with patch('sys.argv', ['script.py', '--config', 'nonexistent.json']):
        with patch('pathlib.Path.exists', return_value=False):
            with patch('builtins.print'):
                # Use a context manager to catch SystemExit
                with pytest.raises(SystemExit) as exc_info:
                    await run_demo(mock_llm_backend)
                assert exc_info.value.code == 1

@pytest.mark.asyncio
async def test_run_demo_single_server(mock_llm_backend):
    """Test run_demo with single server selection."""
    mock_provider = AsyncMock(spec=MCPToolProvider)
    mock_provider.list_available_servers.return_value = ["server1"]
    mock_provider.available_servers = ["server1"]
    
    with patch('agentical.chat_client.MCPToolProvider', return_value=mock_provider):
        with patch('sys.argv', ['script.py']):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('agentical.chat_client.interactive_server_selection', 
                          new_callable=AsyncMock, return_value="server1"):
                    with patch('agentical.chat_client.chat_loop', new_callable=AsyncMock):
                        await run_demo(mock_llm_backend)
                        
                        mock_provider.initialize.assert_called_once()
                        mock_provider.mcp_connect.assert_called_once_with("server1")
                        mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_run_demo_all_servers(mock_llm_backend):
    """Test run_demo with all servers selection."""
    mock_provider = AsyncMock(spec=MCPToolProvider)
    mock_provider.list_available_servers.return_value = ["server1", "server2"]
    mock_provider.available_servers = ["server1", "server2"]
    mock_provider.mcp_connect_all.return_value = [
        ("server1", None),
        ("server2", None)
    ]
    
    with patch('agentical.chat_client.MCPToolProvider', return_value=mock_provider):
        with patch('sys.argv', ['script.py']):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('agentical.chat_client.interactive_server_selection', 
                          new_callable=AsyncMock, return_value=None):
                    with patch('agentical.chat_client.chat_loop', new_callable=AsyncMock):
                        await run_demo(mock_llm_backend)
                        
                        mock_provider.initialize.assert_called_once()
                        mock_provider.mcp_connect_all.assert_called_once()
                        mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_run_demo_all_servers_connection_failure(mock_llm_backend):
    """Test run_demo when all server connections fail."""
    mock_provider = AsyncMock(spec=MCPToolProvider)
    mock_provider.list_available_servers.return_value = ["server1", "server2"]
    mock_provider.available_servers = ["server1", "server2"]
    mock_provider.mcp_connect_all.return_value = [
        ("server1", Exception("Connection failed")),
        ("server2", Exception("Connection failed"))
    ]
    
    with patch('agentical.chat_client.MCPToolProvider', return_value=mock_provider):
        with patch('sys.argv', ['script.py']):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('agentical.chat_client.interactive_server_selection', 
                          new_callable=AsyncMock, return_value=None):
                    with patch('agentical.chat_client.chat_loop', new_callable=AsyncMock):
                        with pytest.raises(Exception, match="Failed to connect to any servers"):
                            await run_demo(mock_llm_backend)
                        
                        mock_provider.cleanup.assert_called_once() 