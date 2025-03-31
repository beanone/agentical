"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import llm_demo

from gemini_backend.gemini_chat import GeminiBackend


async def main():
    await llm_demo.run_demo(GeminiBackend())


if __name__ == "__main__":
    asyncio.run(main()) 