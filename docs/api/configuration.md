# Configuration

This document covers the configuration options and providers in Agentical.

## Server Configuration

Server configurations are defined using the `ServerConfig` class:

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class ServerConfig:
    command: str  # Command to launch the MCP server
    args: list[str]  # Arguments for the server command
    env: Optional[Dict[str, str]] = None  # Optional environment variables
    working_dir: Optional[str] = None  # Optional working directory
```

### Example Configuration File (config.json)

```json
{
    "file-server": {
        "command": "python",
        "args": ["-m", "server.file_server"],
        "env": {
            "PYTHONPATH": "."
        }
    },
    "weather-server": {
        "command": "python",
        "args": ["-m", "server.weather_server"],
        "env": {
            "OPENWEATHERMAP_API_KEY": "${OPENWEATHERMAP_API_KEY}"
        }
    }
}
```

## Environment Variables

Required environment variables depend on your chosen LLM backend and MCP servers:

```bash
# LLM Backend API Keys
OPENAI_API_KEY=your_openai_key     # Required for OpenAI backend
GEMINI_API_KEY=your_gemini_key     # Required for Gemini backend
ANTHROPIC_API_KEY=your_claude_key  # Required for Anthropic backend

# Model Selection (Optional)
OPENAI_MODEL=gpt-4-turbo-preview   # Default model for OpenAI
GEMINI_MODEL=gemini-pro            # Default model for Gemini
ANTHROPIC_MODEL=claude-3-opus      # Default model for Anthropic

# Server-Specific Keys (Set based on your MCP servers)
OPENWEATHERMAP_API_KEY=your_key    # Required for weather server
GITHUB_TOKEN=your_token            # Required for GitHub server
```

## Configuration Providers

### FileBasedMCPConfigProvider

Loads server configurations from a JSON file:

```python
from agentical.mcp.config import FileBasedMCPConfigProvider

config_provider = FileBasedMCPConfigProvider("config.json")
```

### DictBasedMCPConfigProvider

Uses direct dictionary configuration:

```python
from agentical.mcp.config import DictBasedMCPConfigProvider

server_configs = {
    "file-server": ServerConfig(
        command="python",
        args=["-m", "server.file_server"],
        env={"PYTHONPATH": "."}
    )
}
config_provider = DictBasedMCPConfigProvider(server_configs)
```

### Custom Configuration Provider

You can implement your own configuration provider by subclassing `MCPConfigProvider`:

```python
from agentical.mcp.config import MCPConfigProvider

class CustomConfigProvider(MCPConfigProvider):
    async def load_config(self) -> dict[str, ServerConfig]:
        # Implement your custom configuration loading logic
        pass
```

## Configuration Best Practices

1. **Environment Variables**
   - Use environment variables for sensitive data
   - Store API keys in `.env` file
   - Never commit API keys to version control

2. **Server Configuration**
   - Use descriptive server names
   - Set appropriate working directories
   - Configure necessary environment variables

3. **Security**
   - Validate all configuration values
   - Use environment variable substitution
   - Implement proper error handling

4. **Maintenance**
   - Document all configuration options
   - Use configuration templates
   - Version control configurations