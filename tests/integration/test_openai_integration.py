"""Integration tests for OpenAI provider."""

import pytest
import os
from pathlib import Path

from agentical.core import ProviderConfig, ProviderSettings, ToolExecutor, ToolRegistry
from agentical.providers.openai import OpenAIProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_simple_conversation():
    """Test a simple conversation with the OpenAI API."""
    # Get absolute path to .env file
    root_dir = Path(__file__).parent.parent.parent
    env_file = str(root_dir / ".env")
    
    settings = ProviderSettings(env_file=env_file)
    
    # Debug logging
    print(f"\nOPENAI_API_KEY from settings: {settings.openai_api_key is not None}")
    
    # Skip if no API key is configured
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY not set in environment or .env file")
    
    config = ProviderConfig.from_settings("openai", settings)
    print(f"API key in config: {config.api_key is not None}")
    
    provider = OpenAIProvider(config, ToolExecutor(ToolRegistry()))
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Say 'Hello, World!'"}
    ]
    response = await provider.run_conversation(messages, [])
    assert response is not None
    assert len(response) > 0 