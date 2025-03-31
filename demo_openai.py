"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import agentical.chat_client as chat_client

from agentical.openai_backend.openai_chat import OpenAIBackend

async def main():
    await chat_client.run_demo(OpenAIBackend())


if __name__ == "__main__":
    asyncio.run(main()) 