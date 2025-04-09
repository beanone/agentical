# Examples

## Table of Contents
- [Overview](#overview)
- [Basic Usage](#basic-usage)
  - [Simple Query Processing](#simple-query-processing)
  - [Interactive Chat Session](#interactive-chat-session)
- [Custom LLM Backend](#custom-llm-backend)
  - [OpenAI Backend](#openai-backend)
  - [Gemini Backend](#gemini-backend)
  - [Anthropic Backend](#anthropic-backend)
- [Custom Tool Server](#custom-tool-server)
  - [Weather Server](#weather-server)
  - [File Server](#file-server)
  - [GitHub Server](#github-server)
- [Tool Integration](#tool-integration)
  - [Configuration Methods](#configuration-methods)
    - [Using Configuration File](#using-configuration-file)
    - [Using Direct Configuration](#using-direct-configuration)
  - [Tool Implementation Styles](#tool-implementation-styles)
    - [FastMCP Style Example](#fastmcp-style-example)
    - [MCPServer Style Example](#mcpserver-style-example)
- [Advanced Usage](#advanced-usage)
  - [Multiple Server Selection](#multiple-server-selection)
  - [Custom Configuration Provider](#custom-configuration-provider)
  - [Error Handling](#error-handling)
  - [Complex Tool Integration](#complex-tool-integration)
  - [Context Management](#context-management)
- [Best Practices](#best-practices)

## Overview

This document provides practical examples of using Agentical, from basic usage to advanced scenarios and custom implementations.

## Basic Usage

### Simple Query Processing

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider

async def process_single_query():
    # Initialize provider with config
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        # Initialize and connect
        await provider.initialize()
        await provider.mcp_connect_all()

        # Process a query
        response = await provider.process_query(
            "What files are in the current directory?"
        )
        print(response)
    finally:
        # Clean up resources
        await provider.cleanup_all()
```

### Interactive Chat Session

```python
from agentical.chat_client import run_demo
from your_llm_backend import YourLLMBackend

async def main():
    # Initialize your LLM backend
    llm_backend = YourLLMBackend()

    # Run the interactive demo
    await run_demo(llm_backend)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Custom LLM Backend

### OpenAI Backend

```python
from agentical.api import LLMBackend
from openai import AsyncOpenAI
from mcp.types import Tool

class OpenAIBackend(LLMBackend[list]):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def process_query(
        self,
        query: str,
        tools: list[Tool],
        execute_tool: callable,
        context: list | None = None
    ) -> str:
        try:
            # Create messages with context if available
            messages = context or []
            messages.append({"role": "user", "content": query})

            # Get completion from OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.convert_tools(tools)
            )

            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"OpenAI processing failed: {e}")

    def convert_tools(self, tools: list[Tool]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in tools
        ]
```

### Gemini Backend

```python
from agentical.api import LLMBackend
import google.generativeai as genai
from mcp.types import Tool

class GeminiBackend(LLMBackend[list]):
    """Gemini LLM backend implementation."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.chat = None

    async def process_query(
        self,
        query: str,
        tools: list[Tool],
        execute_tool: callable,
        context: list | None = None
    ) -> str:
        try:
            # Initialize or continue chat
            if not self.chat:
                self.chat = self.model.start_chat(history=context or [])

            # Get response with tool support
            response = await self.chat.send_message_async(
                query,
                tools=self.convert_tools(tools)
            )

            return response.text
        except Exception as e:
            raise LLMError(f"Gemini processing failed: {e}")

    def convert_tools(self, tools: list[Tool]) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in tools
        ]
```

### Anthropic Backend

```python
from agentical.api import LLMBackend
from anthropic import AsyncAnthropic
from mcp.types import Tool

class AnthropicBackend(LLMBackend[list]):
    """Anthropic Claude LLM backend implementation."""

    def __init__(self, api_key: str, model: str = "claude-3-opus"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def process_query(
        self,
        query: str,
        tools: list[Tool],
        execute_tool: callable,
        context: list | None = None
    ) -> str:
        try:
            # Create messages with context
            messages = context or []
            messages.append({"role": "user", "content": query})

            # Get completion with tool support
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                tools=self.convert_tools(tools)
            )

            return response.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic processing failed: {e}")

    def convert_tools(self, tools: list[Tool]) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            }
            for tool in tools
        ]
```

## Custom Tool Server

### Weather Server

#### FastMCP Style

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider

async def use_weather_tool():
    # Initialize provider with config file
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        # Connect to weather server
        await provider.initialize()
        await provider.mcp_connect("weather-server")

        # Use the tool
        response = await provider.process_query(
            "What's the weather in Seattle?"
        )
        print(response)
    finally:
        await provider.cleanup_all()
```

#### MCPServer Style

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider
from agentical.mcp.schemas import ServerConfig

async def use_weather_tool():
    # Direct server configuration
    server_configs = {
        "weather-server": ServerConfig(
            command="python",
            args=["-m", "server.weather_server"],
            env={"OPENWEATHER_API_KEY": "your_key"}
        )
    }

    # Initialize provider
    provider = MCPToolProvider(LLMBackend(), server_configs=server_configs)

    try:
        # Connect and use tool
        await provider.initialize()
        await provider.mcp_connect("weather-server")
        response = await provider.process_query(
            "What's the weather in Seattle?"
        )
        print(response)
    finally:
        await provider.cleanup_all()
```

### File Server

```python
"""Filesystem Tool for Agentical Framework.

This module provides MCP-compliant tools for filesystem operations.
"""

import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem")
DEFAULT_WORKSPACE = os.path.expanduser("~/mcp/workspace")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", DEFAULT_WORKSPACE)


class FSError(Exception):
    """Raised when there is an error performing a filesystem operation."""
    pass


@mcp.tool()
async def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        Contents of the file as a string

    Raises:
        FSError: If file cannot be read
    """
    try:
        file_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not file_path.is_file():
            raise FSError(f"File not found: {path}")
        with open(file_path) as f:
            return f.read()
    except Exception as e:
        return str(e)


@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Path to the file to write
        content: Content to write to the file

    Returns:
        Success message

    Raises:
        FSError: If file cannot be written
    """
    try:
        file_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)
        with open(file_path, "w") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return str(e)


@mcp.tool()
async def list_directory(path: str = ".") -> str:
    """List contents of a directory.

    Args:
        path: Path to the directory to list (defaults to current directory)

    Returns:
        Directory listing as a string

    Raises:
        FSError: If directory cannot be listed
    """
    try:
        dir_path = Path(os.path.join(WORKSPACE_DIR, path))
        if not dir_path.exists():
            raise FSError(f"Path not found: {path}")
        if not dir_path.is_dir():
            raise FSError(f"Not a directory: {path}")

        contents = []
        for item in dir_path.iterdir():
            item_type = "dir" if item.is_dir() else "file"
            contents.append(f"{item.name} ({item_type})")

        return "\n".join(contents) if contents else "Directory is empty"
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### GitHub Server

```python
from mcp.server import MCPServer
from mcp.types import Tool
from github import Github
from typing import List, Dict, Any
from mcp import tool

class GitHubServer(MCPServer):
    """GitHub operations server."""

    def __init__(self, token: str):
        super().__init__()
        self.github = Github(token)

    @tool(
        name="list_repos",
        description="List user repositories",
        parameters={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username"
                }
            },
            "required": ["username"]
        }
    )
    async def list_repos(self, username: str) -> List[Dict[str, Any]]:
        """List user repositories."""
        try:
            user = self.github.get_user(username)
            repos = []
            for repo in user.get_repos():
                repos.append({
                    "name": repo.name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language
                })
            return repos
        except Exception as e:
            raise Exception(f"Failed to list repositories: {e}")

    @tool(
        name="get_repo_info",
        description="Get repository information",
        parameters={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                }
            },
            "required": ["owner", "repo"]
        }
    )
    async def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            return {
                "name": repository.name,
                "description": repository.description,
                "stars": repository.stargazers_count,
                "forks": repository.forks_count,
                "language": repository.language,
                "created_at": repository.created_at.isoformat(),
                "updated_at": repository.updated_at.isoformat()
            }
        except Exception as e:
            raise Exception(f"Failed to get repository info: {e}")
```

## Tool Integration

### Configuration Methods

There are two ways to configure Agentical to use MCP tools:

#### Using Configuration File

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider

async def use_weather_tool():
    # Initialize provider with config file
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        # Connect to weather server
        await provider.initialize()
        await provider.mcp_connect("weather-server")

        # Use the tool
        response = await provider.process_query(
            "What's the weather in Seattle?"
        )
        print(response)
    finally:
        await provider.cleanup_all()
```

#### Using Direct Configuration

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider
from agentical.mcp.schemas import ServerConfig

async def use_weather_tool():
    # Direct server configuration
    server_configs = {
        "weather-server": ServerConfig(
            command="python",
            args=["-m", "server.weather_server"],
            env={"OPENWEATHER_API_KEY": "your_key"}
        )
    }

    # Initialize provider
    provider = MCPToolProvider(LLMBackend(), server_configs=server_configs)

    try:
        # Connect and use tool
        await provider.initialize()
        await provider.mcp_connect("weather-server")
        response = await provider.process_query(
            "What's the weather in Seattle?"
        )
        print(response)
    finally:
        await provider.cleanup_all()
```

### Tool Implementation Styles

MCP tools can be implemented in two styles: FastMCP and MCPServer. Both styles are supported by Agentical without any configuration changes.

#### FastMCP Style Example

Here's our weather server implementation using FastMCP style:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

@mcp.tool()
async def get_weather(location: str, units: str = "metric") -> str:
    """Get current weather information for a location."""
    try:
        data = await _get_weather_data(location, units)
        return _format_weather_response(data, units)
    except WeatherError as e:
        return str(e)
```

#### MCPServer Style Example

Note: We currently don't have a MCPServer style example in our codebase. Here's what one would look like:

```python
from mcp.server import MCPServer
from mcp import tool

class WeatherServer(MCPServer):
    @tool(
        name="get_weather",
        description="Get weather for location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "units": {"type": "string", "default": "metric"}
            },
            "required": ["location"]
        }
    )
    async def get_weather(self, location: str, units: str = "metric") -> str:
        """Get current weather information for a location."""
        try:
            data = await self._get_weather_data(location, units)
            return self._format_weather_response(data, units)
        except WeatherError as e:
            return str(e)

if __name__ == "__main__":
    server = WeatherServer()
    server.run()
```

Both styles are fully supported by Agentical - the choice between them is a server implementation detail that doesn't affect how you use the tools through Agentical.

## Advanced Usage

### Multiple Server Selection

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider

async def use_multiple_servers():
    # Initialize provider
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        # Initialize and connect to all servers
        await provider.initialize()
        await provider.mcp_connect_all()

        # Process queries using tools from any server
        response = await provider.process_query(
            "What's the weather in Seattle and list files in the current directory?"
        )
        print(response)
    finally:
        await provider.cleanup_all()
```

### Custom Configuration Provider

```python
from agentical.mcp.config import MCPConfigProvider
from agentical.mcp.schemas import ServerConfig
import yaml

class YAMLConfigProvider(MCPConfigProvider):
    def __init__(self, config_path: str):
        self.config_path = config_path

    async def load_config(self) -> dict[str, ServerConfig]:
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)

        return {
            name: ServerConfig(**config)
            for name, config in raw_config.items()
        }

# Usage
config_provider = YAMLConfigProvider("config.yaml")
provider = MCPToolProvider(llm_backend, config_provider=config_provider)
```

### Error Handling

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider
from agentical.mcp.errors import ConnectionError, ToolExecutionError

async def handle_errors():
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        await provider.initialize()
        await provider.mcp_connect_all()

        try:
            response = await provider.process_query(
                "What's the weather in Seattle?"
            )
            print(response)
        except ToolExecutionError as e:
            print(f"Tool execution failed: {e}")
        except ConnectionError as e:
            print(f"Connection error: {e}")
    finally:
        await provider.cleanup_all()
```

### Context Management

```python
from agentical.api import LLMBackend
from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider

async def manage_context():
    config_provider = FileBasedMCPConfigProvider("config.json")
    provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)

    try:
        await provider.initialize()
        await provider.mcp_connect_all()

        # First query establishes context
        response1 = await provider.process_query(
            "What's the weather in Seattle?"
        )
        print(response1)

        # Second query uses context from first
        response2 = await provider.process_query(
            "How does that compare to New York?"
        )
        print(response2)
    finally:
        await provider.cleanup_all()
```

## Best Practices

1. **Resource Management**
   - Always use `try`/`finally` blocks to ensure proper cleanup
   - Initialize providers before use
   - Clean up resources when done

2. **Error Handling**
   - Handle specific exceptions appropriately
   - Provide meaningful error messages
   - Clean up resources even on errors

3. **Configuration**
   - Use environment variables for sensitive data
   - Validate configurations before use
   - Keep configurations separate from code

4. **Context Management**
   - Maintain conversation context when needed
   - Clear context when starting new conversations
   - Handle context overflow appropriately