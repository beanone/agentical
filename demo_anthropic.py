"""Test script for MCPToolProvider with Anthropic backend."""

import asyncio

from dotenv import load_dotenv

from agentical import chat_client
from agentical.llm.anthropic.anthropic_chat import AnthropicBackend
from agentical.mcp.config import FileBasedMCPConfigProvider

# Load environment variables
load_dotenv()


async def main():
    config_provider = FileBasedMCPConfigProvider("config.json")
    await chat_client.run_demo(AnthropicBackend(), config_provider=config_provider)


if __name__ == "__main__":
    asyncio.run(main())
