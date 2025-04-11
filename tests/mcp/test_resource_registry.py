"""Unit tests for the ResourceRegistry class."""

import pytest
from mcp.types import Resource as MCPResource
from pydantic.networks import AnyUrl

from agentical.mcp.resource_registry import ResourceRegistry


@pytest.fixture
def resource_registry():
    """Create a fresh ResourceRegistry instance for each test."""
    return ResourceRegistry()


@pytest.fixture
def sample_resources():
    """Create sample MCP resources for testing."""
    return [
        MCPResource(
            uri=AnyUrl("https://example.com/resource1"),
            name="resource1",
            description="Test resource 1",
            mimeType="text/plain",
            size=1024,
            annotations=None
        ),
        MCPResource(
            uri=AnyUrl("https://example.com/resource2"),
            name="resource2",
            description="Test resource 2",
            mimeType="application/json",
            size=2048,
            annotations=None
        ),
    ]


async def test_register_server_resources(resource_registry, sample_resources):
    """Test registering resources for a server."""
    # Register resources for a server
    resource_registry.register_server_resources("server1", sample_resources)

    # Verify resources are registered
    assert len(resource_registry.all_resources) == 2
    assert len(resource_registry.resources_by_server["server1"]) == 2
    assert resource_registry.resources_by_server["server1"] == sample_resources


async def test_register_server_resources_replace(resource_registry, sample_resources):
    """Test that registering resources replaces existing ones."""
    # Register initial resources
    resource_registry.register_server_resources("server1", sample_resources)

    # Register new resources for the same server
    new_resources = [
        MCPResource(
            uri=AnyUrl("https://example.com/resource3"),
            name="resource3",
            description="Test resource 3",
            mimeType="text/plain",
            size=1024,
            annotations=None
        )
    ]
    resource_registry.register_server_resources("server1", new_resources)

    # Verify old resources are replaced
    assert len(resource_registry.all_resources) == 1
    assert len(resource_registry.resources_by_server["server1"]) == 1
    assert resource_registry.resources_by_server["server1"] == new_resources


async def test_remove_server_resources(resource_registry, sample_resources):
    """Test removing resources for a server."""
    # Register resources
    resource_registry.register_server_resources("server1", sample_resources)

    # Remove resources
    num_removed = resource_registry.remove_server_resources("server1")

    # Verify resources are removed
    assert num_removed == 2
    assert len(resource_registry.all_resources) == 0
    assert "server1" not in resource_registry.resources_by_server


async def test_remove_server_resources_nonexistent(resource_registry):
    """Test removing resources for a nonexistent server."""
    num_removed = resource_registry.remove_server_resources("nonexistent")
    assert num_removed == 0


async def test_find_resource_server(resource_registry, sample_resources):
    """Test finding which server hosts a resource."""
    # Register resources
    resource_registry.register_server_resources("server1", sample_resources)

    # Find server for a resource
    server = resource_registry.find_resource_server("resource1")
    assert server == "server1"

    # Test with nonexistent resource
    server = resource_registry.find_resource_server("nonexistent")
    assert server is None


async def test_clear(resource_registry, sample_resources):
    """Test clearing all resources."""
    # Register resources for multiple servers
    resource_registry.register_server_resources("server1", sample_resources)
    resource_registry.register_server_resources("server2", sample_resources)

    # Clear all resources
    num_resources, num_servers = resource_registry.clear()

    # Verify everything is cleared
    assert num_resources == 4
    assert num_servers == 2
    assert len(resource_registry.all_resources) == 0
    assert len(resource_registry.resources_by_server) == 0


async def test_get_server_resources(resource_registry, sample_resources):
    """Test getting resources for a server."""
    # Register resources
    resource_registry.register_server_resources("server1", sample_resources)

    # Get resources
    resources = resource_registry.get_server_resources("server1")
    assert resources == sample_resources

    # Test with nonexistent server
    resources = resource_registry.get_server_resources("nonexistent")
    assert resources == []