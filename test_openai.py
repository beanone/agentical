"""Test script for MCPToolProvider, mirroring client.py functionality."""

import asyncio
import llm_demo

from openai_backend.openai_chat import OpenAIBackend

async def main():
    await llm_demo.run_demo(OpenAIBackend())


if __name__ == "__main__":
    asyncio.run(main()) 