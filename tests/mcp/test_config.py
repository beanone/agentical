"""Unit tests for MCP configuration providers.

This module contains tests for the configuration loading and validation functionality,
including both file-based and dictionary-based configuration providers.
"""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from agentical.mcp.config import (
    ConfigurationError,
    DictBasedMCPConfigProvider,
    FileBasedMCPConfigProvider,
)
from agentical.mcp.schemas import MCPConfig, ServerConfig


@pytest.fixture
def valid_server_config():
    """Fixture providing a valid server configuration."""
    return {
        "test_server": ServerConfig(
            command="test_command", args=["--test"], env={"TEST_ENV": "value"}
        )
    }


@pytest.fixture
def valid_config_json():
    """Fixture providing a valid JSON configuration."""
    return {
        "test_server": {
            "command": "test_command",
            "args": ["--test"],
            "env": {"TEST_ENV": "value"},
        }
    }


@pytest.mark.asyncio
async def test_dict_based_provider_valid_config(valid_server_config):
    """Test DictBasedMCPConfigProvider with valid configuration."""
    provider = DictBasedMCPConfigProvider(valid_server_config)
    config = await provider.load_config()

    assert "test_server" in config
    server_config = config["test_server"]
    assert server_config.command == "test_command"
    assert server_config.args == ["--test"]
    assert server_config.env == {"TEST_ENV": "value"}


@pytest.mark.asyncio
async def test_file_based_provider_valid_config(valid_config_json):
    """Test FileBasedMCPConfigProvider with valid configuration file."""
    mock_file = mock_open(read_data=json.dumps(valid_config_json))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        config = await provider.load_config()

    assert "test_server" in config
    server_config = config["test_server"]
    assert server_config.command == "test_command"
    assert server_config.args == ["--test"]
    assert server_config.env == {"TEST_ENV": "value"}


@pytest.mark.asyncio
async def test_file_based_provider_invalid_json():
    """Test FileBasedMCPConfigProvider with invalid JSON."""
    mock_file = mock_open(read_data="invalid json content")

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        with pytest.raises(ConfigurationError, match="Invalid JSON in config file"):
            await provider.load_config()


@pytest.mark.asyncio
async def test_file_based_provider_missing_file():
    """Test FileBasedMCPConfigProvider with missing configuration file."""
    provider = FileBasedMCPConfigProvider("nonexistent.json")
    with pytest.raises(ConfigurationError, match="Failed to load configuration"):
        await provider.load_config()


@pytest.mark.asyncio
async def test_file_based_provider_invalid_config():
    """Test FileBasedMCPConfigProvider with invalid configuration format."""
    invalid_config = {
        "test_server": {
            "command": 123,  # Should be string
            "args": "not_a_list",  # Should be list
        }
    }

    mock_file = mock_open(read_data=json.dumps(invalid_config))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            await provider.load_config()


@pytest.mark.asyncio
async def test_file_based_provider_path_handling():
    """Test FileBasedMCPConfigProvider path handling."""
    # Test with string path
    provider1 = FileBasedMCPConfigProvider("config.json")
    assert isinstance(provider1.config_path, Path)
    assert provider1.config_path.name == "config.json"

    # Test with Path object
    path = Path("test/config.json")
    provider2 = FileBasedMCPConfigProvider(path)
    assert provider2.config_path == path


@pytest.mark.asyncio
async def test_file_based_provider_multiple_servers(valid_config_json):
    """Test FileBasedMCPConfigProvider with multiple server configurations."""
    # Add another server to the configuration
    multi_server_config = valid_config_json.copy()
    multi_server_config["another_server"] = {
        "command": "another_command",
        "args": ["--arg1", "--arg2"],
        "env": {"ENV_VAR": "value"},
    }

    mock_file = mock_open(read_data=json.dumps(multi_server_config))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        config = await provider.load_config()

    assert len(config) == 2
    assert "test_server" in config
    assert "another_server" in config

    another_server = config["another_server"]
    assert another_server.command == "another_command"
    assert another_server.args == ["--arg1", "--arg2"]
    assert another_server.env == {"ENV_VAR": "value"}


@pytest.mark.asyncio
async def test_file_based_provider_empty_config():
    """Test FileBasedMCPConfigProvider with empty configuration."""
    mock_file = mock_open(read_data="{}")

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        with pytest.raises(
            ConfigurationError,
            match="At least one server configuration must be provided",
        ):
            await provider.load_config()


@pytest.mark.asyncio
async def test_dict_based_provider_empty_config():
    """Test DictBasedMCPConfigProvider with empty configuration."""
    provider = DictBasedMCPConfigProvider({})
    config = await provider.load_config()

    assert isinstance(config, dict)
    assert len(config) == 0


@pytest.mark.asyncio
async def test_file_based_provider_minimal_config():
    """Test FileBasedMCPConfigProvider with minimal valid configuration."""
    minimal_config = {"minimal_server": {"command": "test_command", "args": []}}

    mock_file = mock_open(read_data=json.dumps(minimal_config))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        config = await provider.load_config()

    assert "minimal_server" in config
    server_config = config["minimal_server"]
    assert server_config.command == "test_command"
    assert server_config.args == []
    assert server_config.env is None


@pytest.mark.asyncio
async def test_dict_based_provider_config_immutability():
    """Test that DictBasedMCPConfigProvider maintains config immutability."""
    original_config = {
        "test_server": ServerConfig(
            command="test_command", args=["--test"], env={"TEST_ENV": "value"}
        )
    }
    provider = DictBasedMCPConfigProvider(original_config)
    config1 = await provider.load_config()

    # Modify the original config
    original_config["test_server"].command = "modified_command"

    # Load config again and verify it hasn't changed
    config2 = await provider.load_config()
    assert config2["test_server"].command == "test_command"


@pytest.mark.asyncio
async def test_file_based_provider_unicode_handling():
    """Test FileBasedMCPConfigProvider with Unicode characters in configuration."""
    unicode_config = {
        "unicode_server": {
            "command": "测试命令",
            "args": ["--参数"],
            "env": {"变量": "值"},
        }
    }

    mock_file = mock_open(read_data=json.dumps(unicode_config))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        config = await provider.load_config()

    assert "unicode_server" in config
    server_config = config["unicode_server"]
    assert server_config.command == "测试命令"
    assert server_config.args == ["--参数"]
    assert server_config.env == {"变量": "值"}


@pytest.mark.asyncio
async def test_server_config_validation():
    """Test ServerConfig validation rules."""
    # Test empty command
    with pytest.raises(ValueError, match="Command cannot be empty"):
        ServerConfig(command="   ", args=[])

    # Test invalid args
    with pytest.raises(ValueError, match="All args must be non-empty strings"):
        ServerConfig(command="test", args=["", "valid"])

    with pytest.raises(ValueError, match="All args must be non-empty strings"):
        ServerConfig(command="test", args=["valid", "   "])


@pytest.mark.asyncio
async def test_mcp_config_validation():
    """Test MCPConfig validation rules."""
    # Test empty server name
    with pytest.raises(ValueError, match="Server names cannot be empty"):
        config = {"": ServerConfig(command="test", args=[])}
        MCPConfig(servers=config)

    # Test whitespace server name
    with pytest.raises(ValueError, match="Server names cannot be empty"):
        config = {"   ": ServerConfig(command="test", args=[])}
        MCPConfig(servers=config)


@pytest.mark.asyncio
async def test_dict_based_provider_config_deep_copy():
    """Test that DictBasedMCPConfigProvider creates proper deep copies."""
    original_config = {
        "test_server": ServerConfig(
            command="test_command", args=["--test"], env={"TEST_ENV": "value"}
        )
    }
    provider = DictBasedMCPConfigProvider(original_config)
    config1 = await provider.load_config()

    # Modify the first loaded config
    config1["test_server"].env["TEST_ENV"] = "modified"

    # Load again and verify the new config is unaffected
    config2 = await provider.load_config()
    assert config2["test_server"].env["TEST_ENV"] == "value"


@pytest.mark.asyncio
async def test_file_based_provider_invalid_file_encoding():
    """Test FileBasedMCPConfigProvider with invalid file encoding."""
    mock_file = mock_open()
    mock_file.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid utf-8")

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            await provider.load_config()


@pytest.mark.asyncio
async def test_file_based_provider_permission_error():
    """Test FileBasedMCPConfigProvider with file permission error."""
    mock_file = mock_open()
    mock_file.side_effect = PermissionError("Permission denied")

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            await provider.load_config()


@pytest.mark.asyncio
async def test_file_based_provider_large_config():
    """Test FileBasedMCPConfigProvider with a large configuration."""
    large_config = {
        f"server_{i}": {
            "command": f"command_{i}",
            "args": [f"--arg{j}" for j in range(5)],
            "env": {f"ENV_{j}": f"value_{j}" for j in range(5)},
        }
        for i in range(100)
    }

    mock_file = mock_open(read_data=json.dumps(large_config))

    with patch("builtins.open", mock_file):
        provider = FileBasedMCPConfigProvider("config.json")
        config = await provider.load_config()

        assert len(config) == 100
        assert all(f"server_{i}" in config for i in range(100))
        assert all(len(config[f"server_{i}"].args) == 5 for i in range(100))
        assert all(len(config[f"server_{i}"].env) == 5 for i in range(100))
