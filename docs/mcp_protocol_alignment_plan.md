# MCP Protocol Alignment Plan

## Overview

This document outlines the plan to extend our MCP implementation to fully support the MCP protocol by adding resource and prompt template support using the built-in MCP types.

## Goals

1. Add support for MCP resources using `mcp.types.Resource`
2. Add support for MCP prompts using `mcp.types.Prompt`
3. Maintain consistency with existing `ToolRegistry` patterns
4. Ensure proper lifecycle management for all MCP components

## Implementation Plan

### Phase 1: Core Registry Implementation

#### 1. Resource Registry

Create `agentical/mcp/resource_registry.py`:

```python
"""Resource Registry for MCP.

This module provides a centralized registry for managing MCP resources across different
servers. It handles resource registration, lookup, and cleanup operations while
maintaining the relationship between resources and their hosting servers.

Example:
    ```python
    registry = ResourceRegistry()

    # Register resources for a server
    registry.register_server_resources("server1", resources)

    # Find which server hosts a resource
    server = registry.find_resource_server("resource_id")

    # Remove server resources
    num_removed = registry.remove_server_resources("server1")
    ```
"""

import logging
from mcp.types import Resource as MCPResource

logger = logging.getLogger(__name__)

class ResourceRegistry:
    """Manages the registration and lookup of MCP resources.

    This class handles the storage and retrieval of resources across different servers,
    providing a centralized registry for resource management.

    Attributes:
        resources_by_server (Dict[str, List[MCPResource]]): Resources indexed by server
        all_resources (List[MCPResource]): Combined list of all available resources
    """

    def __init__(self):
        """Initialize an empty resource registry."""
        self.resources_by_server: dict[str, list[MCPResource]] = {}
        self.all_resources: list[MCPResource] = []

    def register_server_resources(self, server_name: str, resources: list[MCPResource]) -> None:
        """Register resources for a specific server.

        Args:
            server_name: Name of the server
            resources: List of resources to register

        Note:
            If the server already has registered resources, they will be replaced.
            The all_resources list is updated to include the new resources.
        """
        logger.debug(
            "Registering resources for server",
            extra={"server_name": server_name, "num_resources": len(resources)},
        )

        # If server already exists, remove its resources first
        if server_name in self.resources_by_server:
            self.remove_server_resources(server_name)

        self.resources_by_server[server_name] = resources
        self.all_resources.extend(resources)

        logger.debug(
            "Resources registered successfully",
            extra={"server_name": server_name, "total_resources": len(self.all_resources)},
        )

    def remove_server_resources(self, server_name: str) -> int:
        """Remove all resources for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Number of resources removed

        Note:
            This operation updates both resources_by_server and all_resources collections.
            Resources from other servers are preserved.
        """
        logger.debug("Removing resources for server", extra={"server_name": server_name})

        num_resources_removed = 0
        if server_name in self.resources_by_server:
            server_resources = self.resources_by_server[server_name]
            num_resources_removed = len(server_resources)

            # Get resources from other servers
            other_servers_resources = []
            for other_server, resources in self.resources_by_server.items():
                if other_server != server_name:
                    other_servers_resources.extend(resources)

            # Update all_resources
            self.all_resources = other_servers_resources
            del self.resources_by_server[server_name]

            logger.debug(
                "Server resources removed",
                extra={
                    "server_name": server_name,
                    "num_resources_removed": num_resources_removed,
                    "remaining_resources": len(self.all_resources),
                },
            )

        return num_resources_removed

    def find_resource_server(self, resource_id: str) -> str | None:
        """Find which server hosts a specific resource.

        Args:
            resource_id: ID of the resource to find

        Returns:
            Server name if found, None otherwise

        Note:
            This is an O(n) operation where n is the total number of resources
            across all servers. For better performance with large numbers of
            resources, consider adding an index.
        """
        for server_name, resources in self.resources_by_server.items():
            if any(resource.id == resource_id for resource in resources):
                return server_name
        return None

    def clear(self) -> tuple[int, int]:
        """Clear all registered resources.

        Returns:
            Tuple of (number of resources cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both resources_by_server and all_resources collections are cleared.
        """
        num_resources = len(self.all_resources)
        num_servers = len(self.resources_by_server)

        logger.debug(
            "Clearing resource registry",
            extra={"num_resources": num_resources, "num_servers": num_servers},
        )

        self.resources_by_server.clear()
        self.all_resources.clear()
        return num_resources, num_servers

    def get_server_resources(self, server_name: str) -> list[MCPResource]:
        """Get all resources registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of resources registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.resources_by_server.get(server_name, [])
```

#### 2. Prompt Registry

Create `agentical/mcp/prompt_registry.py`:

```python
"""Prompt Registry for MCP.

This module provides a centralized registry for managing MCP prompts across different
servers. It handles prompt registration, lookup, and cleanup operations while
maintaining the relationship between prompts and their hosting servers.

Example:
    ```python
    registry = PromptRegistry()

    # Register prompts for a server
    registry.register_server_prompts("server1", prompts)

    # Find which server hosts a prompt
    server = registry.find_prompt_server("prompt_name")

    # Remove server prompts
    num_removed = registry.remove_server_prompts("server1")
    ```
"""

import logging
from mcp.types import Prompt as MCPPrompt

logger = logging.getLogger(__name__)

class PromptRegistry:
    """Manages the registration and lookup of MCP prompts.

    This class handles the storage and retrieval of prompts across different servers,
    providing a centralized registry for prompt management.

    Attributes:
        prompts_by_server (Dict[str, List[MCPPrompt]]): Prompts indexed by server
        all_prompts (List[MCPPrompt]): Combined list of all available prompts
    """

    def __init__(self):
        """Initialize an empty prompt registry."""
        self.prompts_by_server: dict[str, list[MCPPrompt]] = {}
        self.all_prompts: list[MCPPrompt] = []

    def register_server_prompts(self, server_name: str, prompts: list[MCPPrompt]) -> None:
        """Register prompts for a specific server.

        Args:
            server_name: Name of the server
            prompts: List of prompts to register

        Note:
            If the server already has registered prompts, they will be replaced.
            The all_prompts list is updated to include the new prompts.
        """
        logger.debug(
            "Registering prompts for server",
            extra={"server_name": server_name, "num_prompts": len(prompts)},
        )

        # If server already exists, remove its prompts first
        if server_name in self.prompts_by_server:
            self.remove_server_prompts(server_name)

        self.prompts_by_server[server_name] = prompts
        self.all_prompts.extend(prompts)

        logger.debug(
            "Prompts registered successfully",
            extra={"server_name": server_name, "total_prompts": len(self.all_prompts)},
        )

    def remove_server_prompts(self, server_name: str) -> int:
        """Remove all prompts for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Number of prompts removed

        Note:
            This operation updates both prompts_by_server and all_prompts collections.
            Prompts from other servers are preserved.
        """
        logger.debug("Removing prompts for server", extra={"server_name": server_name})

        num_prompts_removed = 0
        if server_name in self.prompts_by_server:
            server_prompts = self.prompts_by_server[server_name]
            num_prompts_removed = len(server_prompts)

            # Get prompts from other servers
            other_servers_prompts = []
            for other_server, prompts in self.prompts_by_server.items():
                if other_server != server_name:
                    other_servers_prompts.extend(prompts)

            # Update all_prompts
            self.all_prompts = other_servers_prompts
            del self.prompts_by_server[server_name]

            logger.debug(
                "Server prompts removed",
                extra={
                    "server_name": server_name,
                    "num_prompts_removed": num_prompts_removed,
                    "remaining_prompts": len(self.all_prompts),
                },
            )

        return num_prompts_removed

    def find_prompt_server(self, prompt_name: str) -> str | None:
        """Find which server hosts a specific prompt.

        Args:
            prompt_name: Name of the prompt to find

        Returns:
            Server name if found, None otherwise

        Note:
            This is an O(n) operation where n is the total number of prompts
            across all servers. For better performance with large numbers of
            prompts, consider adding an index.
        """
        for server_name, prompts in self.prompts_by_server.items():
            if any(prompt.name == prompt_name for prompt in prompts):
                return server_name
        return None

    def clear(self) -> tuple[int, int]:
        """Clear all registered prompts.

        Returns:
            Tuple of (number of prompts cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both prompts_by_server and all_prompts collections are cleared.
        """
        num_prompts = len(self.all_prompts)
        num_servers = len(self.prompts_by_server)

        logger.debug(
            "Clearing prompt registry",
            extra={"num_prompts": num_prompts, "num_servers": num_servers},
        )

        self.prompts_by_server.clear()
        self.all_prompts.clear()
        return num_prompts, num_servers

    def get_server_prompts(self, server_name: str) -> list[MCPPrompt]:
        """Get all prompts registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of prompts registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.prompts_by_server.get(server_name, [])
```

### Phase 2: Provider Updates

Update `agentical/mcp/provider.py`:

```python
class MCPToolProvider:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.resource_registry = ResourceRegistry()
        self.prompt_registry = PromptRegistry()

    async def mcp_connect(self, server_name: str) -> None:
        """Connect to a specific MCP server by name."""
        try:
            session = await self.connection_service.connect(
                server_name, self.available_servers[server_name]
            )

            # List and register tools
            tool_response = await session.list_tools()
            self.tool_registry.register_server_tools(server_name, tool_response.tools)

            # List and register resources
            resource_response = await session.list_resources()
            self.resource_registry.register_server_resources(
                server_name, resource_response.resources
            )

            # List and register prompts
            prompt_response = await session.list_prompts()
            self.prompt_registry.register_server_prompts(
                server_name, prompt_response.prompts
            )

            logger.info(
                "Server connection successful",
                extra={
                    "server_name": server_name,
                    "num_tools": len(tool_response.tools),
                    "num_resources": len(resource_response.resources),
                    "num_prompts": len(prompt_response.prompts),
                },
            )

        except Exception as e:
            await self.cleanup_server(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {e!s}")

    async def cleanup_server(self, server_name: str) -> None:
        """Clean up all registries for a server."""
        num_tools = self.tool_registry.remove_server_tools(server_name)
        num_resources = self.resource_registry.remove_server_resources(server_name)
        num_prompts = self.prompt_registry.remove_server_prompts(server_name)

        logger.info(
            "Server cleanup complete",
            extra={
                "server_name": server_name,
                "num_tools_removed": num_tools,
                "num_resources_removed": num_resources,
                "num_prompts_removed": num_prompts,
            },
        )
```

### Phase 3: Unit Tests

#### 1. Resource Registry Tests

Create `tests/mcp/test_resource_registry.py`:

```python
"""Tests for the MCP Resource Registry."""

import pytest
from mcp.types import Resource as MCPResource
from mcp.resource_registry import ResourceRegistry

@pytest.fixture
def registry():
    """Create a fresh resource registry for each test."""
    return ResourceRegistry()

@pytest.fixture
def sample_resources():
    """Create sample resources for testing."""
    return [
        MCPResource(id="res1", type="test"),
        MCPResource(id="res2", type="test"),
    ]

class TestResourceRegistry:
    """Test suite for ResourceRegistry."""

    async def test_register_resources(self, registry, sample_resources):
        """Test registering resources for a server."""
        registry.register_server_resources("server1", sample_resources)
        assert len(registry.all_resources) == 2
        assert len(registry.get_server_resources("server1")) == 2

    async def test_remove_server_resources(self, registry, sample_resources):
        """Test removing resources for a server."""
        registry.register_server_resources("server1", sample_resources)
        num_removed = registry.remove_server_resources("server1")
        assert num_removed == 2
        assert len(registry.all_resources) == 0

    async def test_find_resource_server(self, registry, sample_resources):
        """Test finding which server hosts a resource."""
        registry.register_server_resources("server1", sample_resources)
        server = registry.find_resource_server("res1")
        assert server == "server1"

    async def test_clear(self, registry, sample_resources):
        """Test clearing all resources."""
        registry.register_server_resources("server1", sample_resources)
        num_resources, num_servers = registry.clear()
        assert num_resources == 2
        assert num_servers == 1
        assert len(registry.all_resources) == 0
```

#### 2. Prompt Registry Tests

Create `tests/mcp/test_prompt_registry.py`:

```python
"""Tests for the MCP Prompt Registry."""

import pytest
from mcp.types import Prompt as MCPPrompt
from mcp.prompt_registry import PromptRegistry

@pytest.fixture
def registry():
    """Create a fresh prompt registry for each test."""
    return PromptRegistry()

@pytest.fixture
def sample_prompts():
    """Create sample prompts for testing."""
    return [
        MCPPrompt(name="prompt1", template="test"),
        MCPPrompt(name="prompt2", template="test"),
    ]

class TestPromptRegistry:
    """Test suite for PromptRegistry."""

    async def test_register_prompts(self, registry, sample_prompts):
        """Test registering prompts for a server."""
        registry.register_server_prompts("server1", sample_prompts)
        assert len(registry.all_prompts) == 2
        assert len(registry.get_server_prompts("server1")) == 2

    async def test_remove_server_prompts(self, registry, sample_prompts):
        """Test removing prompts for a server."""
        registry.register_server_prompts("server1", sample_prompts)
        num_removed = registry.remove_server_prompts("server1")
        assert num_removed == 2
        assert len(registry.all_prompts) == 0

    async def test_find_prompt_server(self, registry, sample_prompts):
        """Test finding which server hosts a prompt."""
        registry.register_server_prompts("server1", sample_prompts)
        server = registry.find_prompt_server("prompt1")
        assert server == "server1"

    async def test_clear(self, registry, sample_prompts):
        """Test clearing all prompts."""
        registry.register_server_prompts("server1", sample_prompts)
        num_prompts, num_servers = registry.clear()
        assert num_prompts == 2
        assert num_servers == 1
        assert len(registry.all_prompts) == 0
```

#### 3. Provider Tests

Update `tests/mcp/test_provider.py`:

```python
class TestMCPToolProvider:
    async def test_connect_with_resources_and_prompts(self):
        """Test connecting to a server with resources and prompts."""
        provider = MCPToolProvider()
        await provider.mcp_connect("test_server")

        # Verify tools, resources, and prompts are registered
        assert len(provider.tool_registry.all_tools) > 0
        assert len(provider.resource_registry.all_resources) > 0
        assert len(provider.prompt_registry.all_prompts) > 0

    async def test_cleanup_with_resources_and_prompts(self):
        """Test cleaning up server with resources and prompts."""
        provider = MCPToolProvider()
        await provider.mcp_connect("test_server")
        await provider.cleanup_server("test_server")

        # Verify everything is cleaned up
        assert len(provider.tool_registry.all_tools) == 0
        assert len(provider.resource_registry.all_resources) == 0
        assert len(provider.prompt_registry.all_prompts) == 0
```

### Phase 4: Documentation Updates

1. Update `docs/architecture.md` to include resource and prompt management
2. Update API documentation in `docs/api/` for new components
3. Add examples in `docs/examples/` for resource and prompt usage
4. Update protocol documentation in `docs/protocol/`

## Testing Strategy

1. Unit Tests
   - Test each registry independently
   - Test provider with all registries
   - Test error handling and edge cases
   - Aim for 100% coverage of new code

2. Integration Tests
   - Test full lifecycle with real servers
   - Test cleanup and recovery scenarios
   - Test concurrent operations

3. Documentation Tests
   - Verify all examples in documentation work
   - Test API documentation is accurate
   - Ensure protocol documentation is complete

## Success Criteria

1. All tests pass with good coverage
2. Documentation is complete and accurate
3. Code follows existing patterns
4. Error handling is comprehensive
5. Logging is appropriate and useful
6. Type hints are complete and correct

## Migration Guide

### For Server Implementers

```python
# Before
@mcp.tool()
async def my_tool(): ...

# After
from mcp.types import Resource, Prompt

@mcp.tool()
async def my_tool(): ...

@mcp.resource()
class MyResource(Resource): ...

@mcp.prompt()
class MyPrompt(Prompt): ...
```

### For Client Code

```python
# Before
await provider.mcp_connect(server_name)

# After - resources and prompts are automatically managed
await provider.mcp_connect(server_name)
resources = provider.resource_registry.get_server_resources(server_name)
prompts = provider.prompt_registry.get_server_prompts(server_name)
```