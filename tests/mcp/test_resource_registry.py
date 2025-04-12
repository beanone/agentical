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
            annotations=None,
        ),
        MCPResource(
            uri=AnyUrl("https://example.com/resource2"),
            name="resource2",
            description="Test resource 2",
            mimeType="application/json",
            size=2048,
            annotations=None,
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
            annotations=None,
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


async def test_validate_resource_invalid_type(resource_registry):
    """Test validation of invalid resource type."""
    with pytest.raises(TypeError, match="Resource must be an MCPResource"):
        resource_registry._validate_resource("not_a_resource")


async def test_validate_resource_empty_name(resource_registry):
    """Test validation of resource with empty name."""
    with pytest.raises(ValueError, match="Resource name cannot be empty"):
        resource_registry._validate_resource(
            MCPResource(
                uri=AnyUrl("https://example.com/resource"),
                name="",
                description="test",
                mimeType="text/plain",
                size=1024,
                annotations=None,
            )
        )


async def test_validate_resources_invalid_list_type(resource_registry):
    """Test validation of invalid resources list type."""
    with pytest.raises(TypeError, match="Resources must be a list"):
        resource_registry._validate_resources("not_a_list", "server1")


async def test_validate_resources_duplicate_names(resource_registry):
    """Test validation of resources with duplicate names."""
    duplicate_resources = [
        MCPResource(
            uri=AnyUrl("https://example.com/resource1"),
            name="duplicate",
            description="test1",
            mimeType="text/plain",
            size=1024,
            annotations=None,
        ),
        MCPResource(
            uri=AnyUrl("https://example.com/resource2"),
            name="duplicate",
            description="test2",
            mimeType="text/plain",
            size=1024,
            annotations=None,
        ),
    ]
    with pytest.raises(ValueError, match="Duplicate resource names found"):
        resource_registry._validate_resources(duplicate_resources, "server1")


async def test_register_server_resources_error_handling(resource_registry):
    """Test error handling during resource registration."""
    # Test with invalid resources list
    with pytest.raises(TypeError):
        resource_registry.register_server_resources("server1", "not_a_list")

    # Test with duplicate resource names
    duplicate_resources = [
        MCPResource(
            uri=AnyUrl("https://example.com/resource1"),
            name="duplicate",
            description="test1",
            mimeType="text/plain",
            size=1024,
            annotations=None,
        ),
        MCPResource(
            uri=AnyUrl("https://example.com/resource2"),
            name="duplicate",
            description="test2",
            mimeType="text/plain",
            size=1024,
            annotations=None,
        ),
    ]
    with pytest.raises(ValueError):
        resource_registry.register_server_resources("server1", duplicate_resources)


async def test_remove_server_resources_error_handling(
    resource_registry, sample_resources
):
    """Test error handling during resource removal."""
    # Register resources first
    resource_registry.register_server_resources("server1", sample_resources)

    # Mock an error during removal
    original_resources = resource_registry.resources_by_server["server1"]
    resource_registry.resources_by_server["server1"] = None  # This will cause an error

    with pytest.raises(Exception):
        resource_registry.remove_server_resources("server1")

    # Restore the resources to avoid affecting other tests
    resource_registry.resources_by_server["server1"] = original_resources


async def test_find_resource_server_invalid_name(resource_registry):
    """Test finding resource server with invalid resource name."""
    # Test with empty resource name
    assert resource_registry.find_resource_server("") is None

    # Test with non-string resource name
    assert resource_registry.find_resource_server(123) is None


async def test_clear_error_handling(resource_registry, sample_resources):
    """Test error handling during registry clearing."""
    # Register resources first
    resource_registry.register_server_resources("server1", sample_resources)

    # Mock an error during clearing
    original_resources = resource_registry.all_resources
    resource_registry.all_resources = None  # This will cause an error

    with pytest.raises(Exception):
        resource_registry.clear()

    # Restore the resources to avoid affecting other tests
    resource_registry.all_resources = original_resources


async def test_register_server_resources_empty_list(resource_registry):
    """Test registering an empty list of resources."""
    resource_registry.register_server_resources("server1", [])
    assert len(resource_registry.all_resources) == 0
    assert len(resource_registry.resources_by_server["server1"]) == 0


async def test_register_server_resources_multiple_servers(
    resource_registry, sample_resources
):
    """Test registering resources for multiple servers."""
    # Register resources for first server
    resource_registry.register_server_resources("server1", sample_resources)

    # Register different resources for second server
    other_resources = [
        MCPResource(
            uri=AnyUrl("https://example.com/resource3"),
            name="resource3",
            description="Test resource 3",
            mimeType="text/plain",
            size=1024,
            annotations=None,
        )
    ]
    resource_registry.register_server_resources("server2", other_resources)

    # Verify both servers' resources are registered correctly
    assert len(resource_registry.all_resources) == 3
    assert len(resource_registry.resources_by_server["server1"]) == 2
    assert len(resource_registry.resources_by_server["server2"]) == 1
    assert resource_registry.resources_by_server["server1"] == sample_resources
    assert resource_registry.resources_by_server["server2"] == other_resources


async def test_remove_server_resources_verify_state(
    resource_registry, sample_resources
):
    """Test that removing server resources maintains correct state."""
    # Register resources for multiple servers
    resource_registry.register_server_resources("server1", sample_resources)
    resource_registry.register_server_resources("server2", sample_resources)

    # Remove resources for one server
    num_removed = resource_registry.remove_server_resources("server1")

    # Verify state
    assert num_removed == 2
    assert "server1" not in resource_registry.resources_by_server
    assert "server1" not in resource_registry._resource_names
    assert len(resource_registry.all_resources) == 2
    assert len(resource_registry.resources_by_server["server2"]) == 2
