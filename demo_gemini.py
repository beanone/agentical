"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import agentical.chat_client as chat_client

from agentical.gemini_backend.gemini_chat import GeminiBackend


async def main():
    await chat_client.run_demo(GeminiBackend())


if __name__ == "__main__":
    asyncio.run(main()) 