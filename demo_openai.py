"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import logging

from agentical import chat_client
from agentical.logging_config import setup_logging
from agentical.openai_backend.openai_chat import OpenAIBackend


async def main():
    # Enable info logging
    setup_logging(logging.INFO)
    await chat_client.run_demo(OpenAIBackend())


if __name__ == "__main__":
    asyncio.run(main())
