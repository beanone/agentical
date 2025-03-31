"""Test script for MCPToolProvider with Anthropic backend."""

import asyncio
import llm_demo

from anthropic_backend.anthropic_chat import AnthropicBackend


async def main():
    await llm_demo.run_demo(AnthropicBackend())


if __name__ == "__main__":
    asyncio.run(main()) 