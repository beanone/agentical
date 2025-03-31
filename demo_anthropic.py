"""Test script for MCPToolProvider with Anthropic backend."""

import asyncio
import agentical.chat_client as chat_client

from agentical.anthropic_backend.anthropic_chat import AnthropicBackend


async def main():
    await chat_client.run_demo(AnthropicBackend())


if __name__ == "__main__":
    asyncio.run(main()) 