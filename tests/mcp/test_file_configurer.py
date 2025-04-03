"""Test suite for the FileConfigProvider class."""

import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from agentical.mcp.file_configurer import FileConfigProvider


@pytest.fixture
def valid_config():
    """Fixture providing a valid server configuration."""
    return {
        "servers": {
            "server1": {
                "command": "python",
                "args": ["-m", "server1"]
            },
            "server2": {
                "command": "python3",
                "args": ["-m", "server2", "--port", "8080"]
            }
        }
    }


@pytest.fixture
def config_file(tmp_path, valid_config):
    """Fixture creating a temporary config file with valid content."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    return config_path


@pytest.fixture
def provider(config_file):
    """Fixture providing a FileConfigProvider instance."""
    return FileConfigProvider(config_file)


@pytest.mark.asyncio
async def test_load_valid_config(tmp_path, valid_config):
    """Test loading a valid configuration file."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    config = await provider.load_config()
    
    assert "server1" in config
    assert "server2" in config
    assert config["server1"]["command"] == "python"
    assert config["server2"]["command"] == "python3"


@pytest.mark.asyncio
async def test_get_server_config(tmp_path, valid_config):
    """Test retrieving configuration for a specific server."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    server_config = await provider.get_server_config("server1")
    
    assert server_config["command"] == "python"
    assert server_config["args"] == ["-m", "server1"]


@pytest.mark.asyncio
async def test_list_available_servers(tmp_path, valid_config):
    """Test listing available servers."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    servers = await provider.list_available_servers()
    
    assert set(servers) == {"server1", "server2"}


@pytest.mark.asyncio
async def test_nonexistent_config_file():
    """Test handling of nonexistent configuration file."""
    provider = FileConfigProvider("nonexistent.json")
    with pytest.raises(FileNotFoundError):
        await provider.load_config()


@pytest.mark.asyncio
async def test_invalid_json(tmp_path):
    """Test handling of invalid JSON file."""
    config_path = tmp_path / "invalid.json"
    with open(config_path, "w") as f:
        f.write("invalid json")
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(json.JSONDecodeError):
        await provider.load_config()


@pytest.mark.asyncio
async def test_invalid_config_structure(tmp_path):
    """Test handling of invalid configuration structure."""
    invalid_config = {"not_servers": {}}
    config_path = tmp_path / "invalid_structure.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "servers" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_required_fields(tmp_path):
    """Test handling of missing required fields."""
    invalid_config = {"servers": {"server1": {}}}
    config_path = tmp_path / "missing_fields.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "Field required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_field_types(tmp_path):
    """Test handling of invalid field types."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": ["not a string"],
                "args": ["-m", "server1"]
            }
        }
    }
    config_path = tmp_path / "invalid_types.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "Input should be a valid string" in str(exc_info.value)


@pytest.mark.asyncio
async def test_nonexistent_server(tmp_path, valid_config):
    """Test handling of nonexistent server request."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(KeyError) as exc_info:
        await provider.get_server_config("nonexistent")
    assert "not found in configuration" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_config_path():
    """Test handling of empty configuration path."""
    with pytest.raises(ValueError) as exc_info:
        FileConfigProvider("")
    assert "Configuration path cannot be empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_command_string(tmp_path):
    """Test handling of empty command string."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": "   ",
                "args": ["-m", "server1"]
            }
        }
    }
    config_path = tmp_path / "empty_command.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "Command cannot be empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_args_string(tmp_path):
    """Test handling of empty argument string."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": "python",
                "args": ["", "  "]
            }
        }
    }
    config_path = tmp_path / "empty_args.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "All arguments must be non-empty strings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_caching_behavior(tmp_path, valid_config):
    """Test that configurations are properly cached."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    
    # First load should read from file
    config1 = await provider.load_config()
    
    # Second load should use cache
    config2 = await provider.load_config()
    
    assert config1 is not None
    assert config2 is not None
    assert config1 == config2


@pytest.mark.asyncio
async def test_config_file_changes(tmp_path, valid_config):
    """Test handling of configuration file changes."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    await provider.load_config()
    
    # Modify the config file
    modified_config = {
        "servers": {
            "server1": {
                "command": "python3",
                "args": ["-m", "modified"]
            }
        }
    }
    with open(config_path, "w") as f:
        json.dump(modified_config, f)
    
    # Load again should reflect changes
    new_config = await provider.load_config()
    assert new_config["server1"]["command"] == "python3"
    assert new_config["server1"]["args"] == ["-m", "modified"]


@pytest.mark.asyncio
async def test_get_config_before_load(tmp_path, valid_config):
    """Test getting server config before loading any configuration."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config, f)
    
    provider = FileConfigProvider(config_path)
    config = await provider.get_server_config("server1")  # Should trigger load
    
    assert config["command"] == "python"
    assert config["args"] == ["-m", "server1"]


@pytest.mark.asyncio
async def test_list_servers_before_load():
    """Test listing servers before loading any configuration."""
    provider = FileConfigProvider("nonexistent_config.json")
    with pytest.raises(FileNotFoundError):
        await provider.list_available_servers()  # Should trigger load


@pytest.mark.asyncio
async def test_mixed_valid_invalid_args(tmp_path):
    """Test validation with a mix of valid and invalid arguments."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": "python",
                "args": ["valid", "", "also_valid", "  ", "another_valid"]
            }
        }
    }
    config_path = tmp_path / "mixed_args.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "All arguments must be non-empty strings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_command_field(tmp_path):
    """Test validation when 'command' field is missing (line 110)."""
    # Create a config with a server that has a valid dict but no command field
    invalid_config = {
        "servers": {
            "server1": {
                "args": ["-m", "server1"],
                "cwd": "/some/path"
            }
        }
    }
    config_path = tmp_path / "missing_command.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    
    # This should raise ValidationError due to missing command field
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    
    # Verify the error message
    assert "Field required" in str(exc_info.value)
    assert "command" in str(exc_info.value)


@pytest.mark.asyncio
async def test_command_not_string(tmp_path):
    """Test validation when 'command' is not a string."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": 123,
                "args": ["-m", "server1"]
            }
        }
    }
    config_path = tmp_path / "invalid_command_type.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "Input should be a valid string" in str(exc_info.value)


@pytest.mark.asyncio
async def test_args_not_list(tmp_path):
    """Test validation when 'args' is not a list."""
    invalid_config = {
        "servers": {
            "server1": {
                "command": "python",
                "args": "not a list"
            }
        }
    }
    config_path = tmp_path / "invalid_args_type.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    assert "Input should be a valid list" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_config_missing_command(tmp_path):
    """Test validation when server config is missing command field."""
    # Create a config file with missing command field
    config = {
        "servers": {
            "server1": {
                "args": ["arg1", "arg2"],
                "cwd": "/path/to/cwd"
            }
        }
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    
    provider = FileConfigProvider(config_path)
    
    # Try to get server config - this should trigger validation
    with pytest.raises(ValidationError) as exc_info:
        await provider.get_server_config("server1")
    
    # Verify the error message
    assert "Field required" in str(exc_info.value)
    assert "command" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dict_missing_command_field(tmp_path):
    """Test validation when server config is a dict but missing command field."""
    # Create a config where server_config is definitely a dict but missing command
    invalid_config = {
        "servers": {
            "server1": dict(
                args=["-m", "server1"],
                cwd="/some/path"
            )
        }
    }
    config_path = tmp_path / "dict_missing_command.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)
    
    provider = FileConfigProvider(config_path)
    
    # This should pass the dict check but fail on missing command
    with pytest.raises(ValidationError) as exc_info:
        await provider.load_config()
    
    # Verify the error message
    assert "Field required" in str(exc_info.value)
    assert "command" in str(exc_info.value) 