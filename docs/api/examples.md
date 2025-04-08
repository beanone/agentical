# Examples

This document provides practical examples of using Agentical.

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

### OpenAI Backend Example

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

## Custom Tool Server

### Weather Server Example

```python
from mcp.server import MCPServer
from mcp.types import Tool
import aiohttp

class WeatherServer(MCPServer):
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

        # Register weather tool
        self.register_tool(
            Tool(
                name="get_weather",
                description="Get current weather for a location",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or coordinates"
                        }
                    },
                    "required": ["location"]
                }
            ),
            self.get_weather
        )

    async def get_weather(self, location: str) -> dict:
        """Get weather information for a location."""
        async with aiohttp.ClientSession() as session:
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }
            async with session.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params=params
            ) as response:
                data = await response.json()
                if response.status != 200:
                    raise Exception(f"Weather API error: {data['message']}")
                return {
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"]
                }

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    server = WeatherServer(os.getenv("OPENWEATHERMAP_API_KEY"))
    server.run()
```

## Advanced Usage

### Multiple Server Selection

```python
from agentical.mcp import MCPToolProvider

async def connect_to_servers(provider: MCPToolProvider):
    # List available servers
    servers = provider.list_available_servers()
    print("Available servers:", servers)

    # Connect to specific servers
    for server in ["file-server", "weather-server"]:
        try:
            await provider.mcp_connect(server)
            print(f"Connected to {server}")
        except Exception as e:
            print(f"Failed to connect to {server}: {e}")
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

### Error Handling Example

```python
from agentical.mcp import MCPToolProvider, ConnectionError

async def robust_query_processing(provider: MCPToolProvider, query: str):
    max_retries = 3
    delay = 1.0

    for attempt in range(max_retries):
        try:
            return await provider.process_query(query)
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            print(f"Connection error (attempt {attempt + 1}): {e}")
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise
```