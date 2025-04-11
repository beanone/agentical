"""Unit tests for the PromptRegistry class."""

import pytest
from mcp.types import Prompt as MCPPrompt, PromptArgument

from agentical.mcp.prompt_registry import PromptRegistry


@pytest.fixture
def prompt_registry():
    """Create a fresh PromptRegistry instance for each test."""
    return PromptRegistry()


@pytest.fixture
def sample_prompts():
    """Create sample MCP prompts for testing."""
    return [
        MCPPrompt(
            name="prompt1",
            description="Test prompt 1",
            arguments=[
                PromptArgument(
                    name="arg1",
                    description="First argument",
                    type="string",
                    required=True
                )
            ]
        ),
        MCPPrompt(
            name="prompt2",
            description="Test prompt 2",
            arguments=[
                PromptArgument(
                    name="arg2",
                    description="Second argument",
                    type="number",
                    required=False
                )
            ]
        ),
    ]


async def test_register_server_prompts(prompt_registry, sample_prompts):
    """Test registering prompts for a server."""
    # Register prompts for a server
    prompt_registry.register_server_prompts("server1", sample_prompts)

    # Verify prompts are registered
    assert len(prompt_registry.all_prompts) == 2
    assert len(prompt_registry.prompts_by_server["server1"]) == 2
    assert prompt_registry.prompts_by_server["server1"] == sample_prompts


async def test_register_server_prompts_replace(prompt_registry, sample_prompts):
    """Test that registering prompts replaces existing ones."""
    # Register initial prompts
    prompt_registry.register_server_prompts("server1", sample_prompts)

    # Register new prompts for the same server
    new_prompts = [MCPPrompt(name="prompt3", description="Test prompt 3")]
    prompt_registry.register_server_prompts("server1", new_prompts)

    # Verify old prompts are replaced
    assert len(prompt_registry.all_prompts) == 1
    assert len(prompt_registry.prompts_by_server["server1"]) == 1
    assert prompt_registry.prompts_by_server["server1"] == new_prompts


async def test_remove_server_prompts(prompt_registry, sample_prompts):
    """Test removing prompts for a server."""
    # Register prompts
    prompt_registry.register_server_prompts("server1", sample_prompts)

    # Remove prompts
    num_removed = prompt_registry.remove_server_prompts("server1")

    # Verify prompts are removed
    assert num_removed == 2
    assert len(prompt_registry.all_prompts) == 0
    assert "server1" not in prompt_registry.prompts_by_server


async def test_remove_server_prompts_nonexistent(prompt_registry):
    """Test removing prompts for a nonexistent server."""
    num_removed = prompt_registry.remove_server_prompts("nonexistent")
    assert num_removed == 0


async def test_find_prompt_server(prompt_registry, sample_prompts):
    """Test finding which server hosts a prompt."""
    # Register prompts
    prompt_registry.register_server_prompts("server1", sample_prompts)

    # Find server for a prompt
    server = prompt_registry.find_prompt_server("prompt1")
    assert server == "server1"

    # Test with nonexistent prompt
    server = prompt_registry.find_prompt_server("nonexistent")
    assert server is None


async def test_clear(prompt_registry, sample_prompts):
    """Test clearing all prompts."""
    # Register prompts for multiple servers
    prompt_registry.register_server_prompts("server1", sample_prompts)
    prompt_registry.register_server_prompts("server2", sample_prompts)

    # Clear all prompts
    num_prompts, num_servers = prompt_registry.clear()

    # Verify everything is cleared
    assert num_prompts == 4
    assert num_servers == 2
    assert len(prompt_registry.all_prompts) == 0
    assert len(prompt_registry.prompts_by_server) == 0


async def test_get_server_prompts(prompt_registry, sample_prompts):
    """Test getting prompts for a server."""
    # Register prompts
    prompt_registry.register_server_prompts("server1", sample_prompts)

    # Get prompts
    prompts = prompt_registry.get_server_prompts("server1")
    assert prompts == sample_prompts

    # Test with nonexistent server
    prompts = prompt_registry.get_server_prompts("nonexistent")
    assert prompts == []