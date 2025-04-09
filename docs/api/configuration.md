# Configuration

## Table of Contents
- [Overview](#overview)
- [Configuration Structure](#configuration-structure)
  - [Server Configuration](#server-configuration)
  - [LLM Configuration](#llm-configuration)
  - [Tool Configuration](#tool-configuration)
- [Configuration Validation](#configuration-validation)
  - [Schema Validation](#schema-validation)
  - [Value Validation](#value-validation)
  - [Environment Validation](#environment-validation)
- [Configuration Providers](#configuration-providers)
  - [File-Based Provider](#file-based-provider)
  - [Dictionary-Based Provider](#dictionary-based-provider)
  - [Custom Provider](#custom-provider)
- [Environment Variables](#environment-variables)
- [Configuration Inheritance](#configuration-inheritance)
- [Best Practices](#best-practices)

## Overview

This document covers the configuration system in Agentical, including configuration structure, validation, providers, and best practices.

## Configuration Structure

### Server Configuration

Server configurations are defined using the `ServerConfig` class:

```python
from dataclasses import dataclass
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, validator

class ServerConfig(BaseModel):
    """Configuration for an MCP server."""
    name: str = Field(..., description="Server name")
    command: str = Field(..., description="Command to launch the server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    working_dir: Optional[str] = Field(None, description="Working directory")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of connection retries")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")

    @validator('name')
    def validate_name(cls, v):
        """Validate server name."""
        if not v or not v.strip():
            raise ValueError("Server name cannot be empty")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Server name can only contain alphanumeric characters, hyphens, and underscores")
        return v

    @validator('timeout', 'retry_attempts', 'health_check_interval')
    def validate_positive_integer(cls, v):
        """Validate positive integers."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
```

### LLM Configuration

LLM configurations are defined using the `LLMConfig` class:

```python
class LLMConfig(BaseModel):
    """Configuration for an LLM backend."""
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    timeout: int = Field(default=60, description="Request timeout in seconds")

    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature value."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        """Validate max tokens value."""
        if v < 1:
            raise ValueError("Max tokens must be positive")
        return v
```

### Tool Configuration

Tool configurations are defined using the `ToolConfig` class:

```python
class ToolConfig(BaseModel):
    """Configuration for a tool."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Parameter schema")
    timeout: int = Field(default=30, description="Execution timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of execution retries")
    rate_limit: Optional[int] = Field(None, description="Requests per minute limit")

    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameter schema."""
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")
        if 'type' not in v or v['type'] != 'object':
            raise ValueError("Parameter schema must be an object type")
        if 'properties' not in v:
            raise ValueError("Parameter schema must have properties")
        return v
```

## Configuration Validation

### Schema Validation

Configuration schemas are validated using Pydantic:

```python
from pydantic import BaseSettings, Field, validator
from typing import Dict, Optional

class AgenticalConfig(BaseSettings):
    """Root configuration for Agentical."""
    servers: Dict[str, ServerConfig] = Field(default_factory=dict)
    llm: LLMConfig
    tools: Dict[str, ToolConfig] = Field(default_factory=dict)
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(None)

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()
```

### Value Validation

Configuration values are validated at runtime:

```python
class ConfigValidator:
    """Validates configuration values at runtime."""

    def validate_server_config(self, config: ServerConfig) -> None:
        """Validate server configuration."""
        # Check command exists
        if not shutil.which(config.command):
            raise ValueError(f"Command not found: {config.command}")

        # Check working directory
        if config.working_dir and not os.path.isdir(config.working_dir):
            raise ValueError(f"Working directory not found: {config.working_dir}")

        # Check environment variables
        for key, value in config.env.items():
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                if env_var not in os.environ:
                    raise ValueError(f"Environment variable not set: {env_var}")

    def validate_llm_config(self, config: LLMConfig) -> None:
        """Validate LLM configuration."""
        # Check API key format
        if not config.api_key or len(config.api_key) < 20:
            raise ValueError("Invalid API key format")

        # Check model availability
        if not self._is_model_available(config.provider, config.model):
            raise ValueError(f"Model not available: {config.model}")
```

### Environment Validation

Environment variables are validated before use:

```python
class EnvironmentValidator:
    """Validates environment variables."""

    REQUIRED_VARS = {
        'OPENAI_API_KEY': r'^sk-[A-Za-z0-9]{32,}$',
        'GEMINI_API_KEY': r'^AIza[A-Za-z0-9_-]{35}$',
        'ANTHROPIC_API_KEY': r'^sk-ant-[A-Za-z0-9]{32,}$'
    }

    def validate_environment(self) -> None:
        """Validate required environment variables."""
        for var, pattern in self.REQUIRED_VARS.items():
            value = os.environ.get(var)
            if not value:
                raise ValueError(f"Required environment variable not set: {var}")
            if not re.match(pattern, value):
                raise ValueError(f"Invalid format for environment variable: {var}")
```

## Configuration Providers

### File-Based Provider

Loads server configurations from a JSON file:

```python
from agentical.mcp.config import FileBasedMCPConfigProvider

config_provider = FileBasedMCPConfigProvider("config.json")
```

### Dictionary-Based Provider

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

### Custom Provider

You can implement your own configuration provider by subclassing `MCPConfigProvider`:

```python
from agentical.mcp.config import MCPConfigProvider

class CustomConfigProvider(MCPConfigProvider):
    async def load_config(self) -> dict[str, ServerConfig]:
        # Implement your custom configuration loading logic
        pass
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

## Configuration Inheritance

Configurations support inheritance and overrides:

```python
class ConfigInheritance:
    """Handles configuration inheritance and overrides."""

    def merge_configs(
        self,
        base_config: dict,
        override_config: dict
    ) -> dict:
        """Merge two configurations with override precedence."""
        merged = base_config.copy()

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self.merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def apply_overrides(
        self,
        config: dict,
        overrides: dict
    ) -> dict:
        """Apply configuration overrides."""
        return self.merge_configs(config, overrides)
```

## Best Practices

1. **Configuration Design**
   - Use type-safe configuration classes
   - Implement comprehensive validation
   - Support configuration inheritance
   - Document all configuration options
   - Version control configurations

2. **Security**
   - Use environment variables for secrets
   - Validate all configuration values
   - Implement proper error handling
   - Use secure configuration storage
   - Rotate sensitive values regularly

3. **Maintenance**
   - Keep configurations modular
   - Use configuration templates
   - Document changes
   - Test configuration changes
   - Monitor configuration usage

4. **Validation**
   - Validate at load time
   - Validate at runtime
   - Check environment variables
   - Verify file permissions
   - Test configuration combinations