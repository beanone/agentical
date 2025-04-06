"""Test script for MCPToolProvider with Anthropic backend."""

import asyncio
from dotenv import load_dotenv
import agentical.chat_client as chat_client

from agentical.anthropic_backend.anthropic_chat import AnthropicBackend

# Load environment variables
load_dotenv()

async def main():
    await chat_client.run_demo(AnthropicBackend())


if __name__ == "__main__":
    asyncio.run(main()) 