"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio

from agentical import chat_client
from agentical.llm.gemini.gemini_chat import GeminiBackend
from agentical.mcp.config import FileBasedMCPConfigProvider


async def main():
    config_provider = FileBasedMCPConfigProvider("config.json")
    await chat_client.run_demo(GeminiBackend(), config_provider=config_provider)


if __name__ == "__main__":
    asyncio.run(main())
