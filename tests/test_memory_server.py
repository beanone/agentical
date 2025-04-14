"""Test cases for memory server."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from server.memory_server import (
    create_entities,
    create_relations,
    add_observations,
    delete_entities,
    delete_observations,
    delete_relations,
    read_graph,
    search_nodes,
    open_nodes,
    EntityType,
    RelationType,
    MEMORY_FILE_NAME,
    clear_graph,
    get_graph,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir
        # Cleanup is handled by the TemporaryDirectory context manager


@pytest.fixture
def setup_memory(temp_dir):
    """Set up a temporary memory file for testing."""
    # Set up environment variables for testing
    os.environ["MEMORY_FILE_PATH"] = temp_dir
    os.environ["LOCAL_STORAGE"] = "false"

    # Clear any existing graph state
    clear_graph()

    # Create an empty memory file
    memory_path = Path(temp_dir) / MEMORY_FILE_NAME
    if memory_path.exists():
        memory_path.unlink()
    memory_path.touch()

    yield

    # Cleanup environment variables
    if "MEMORY_FILE_PATH" in os.environ:
        del os.environ["MEMORY_FILE_PATH"]
    if "LOCAL_STORAGE" in os.environ:
        del os.environ["LOCAL_STORAGE"]

    # Clear graph state after test
    clear_graph()


@pytest.mark.asyncio
class TestReadGraph:
    """Test cases for read_graph function."""

    async def test_read_empty_graph(self, setup_memory, temp_dir):
        """Test reading an empty graph."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        result = await read_graph()
        assert result == {"entities": {}, "relations": []}

    async def test_read_graph_with_data(self, setup_memory, temp_dir):
        """Test reading a graph with data."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # Create test data using the API
        entities = [
            {
                "name": "test_project",
                "entity_type": "project",
                "observations": ["Test project"]
            },
            {
                "name": "test_component",
                "entity_type": "component",
                "observations": ["Test component"]
            }
        ]
        await create_entities(entities)

        relations = [{
            "from_entity": "test_project",
            "to_entity": "test_component",
            "relation_type": "has_component"
        }]
        await create_relations(relations)

        result = await read_graph()
        assert "test_project" in result["entities"]
        assert len(result["relations"]) == 1
        assert result["relations"][0]["from_entity"] == "test_project"
        assert result["relations"][0]["to_entity"] == "test_component"
        assert result["relations"][0]["relation_type"] == "has_component"


@pytest.mark.asyncio
class TestCreateEntities:
    """Test cases for create_entities function."""

    async def test_create_single_entity(self, setup_memory, temp_dir):
        """Test creating a single entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        entities = [{
            "name": "test_project",
            "entity_type": "project",
            "observations": ["Test project"]
        }]
        result = await create_entities(entities)
        assert "Successfully created entities" in result

        # Verify entity was created
        graph = await read_graph()
        assert "test_project" in graph["entities"]
        assert graph["entities"]["test_project"]["entity_type"] == "project"
        assert graph["entities"]["test_project"]["observations"] == ["Test project"]

    async def test_create_multiple_entities(self, setup_memory, temp_dir):
        """Test creating multiple entities."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": ["Project 1"]
            },
            {
                "name": "project2",
                "entity_type": "project",
                "observations": ["Project 2"]
            }
        ]
        result = await create_entities(entities)
        assert "Successfully created entities" in result

        # Verify entities were created
        graph = await read_graph()
        assert "project1" in graph["entities"]
        assert "project2" in graph["entities"]
        assert graph["entities"]["project1"]["observations"] == ["Project 1"]
        assert graph["entities"]["project2"]["observations"] == ["Project 2"]

    async def test_create_duplicate_entity(self, setup_memory, temp_dir):
        """Test creating a duplicate entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create an entity
        entities = [{
            "name": "test_project",
            "entity_type": "project",
            "observations": ["Original project"]
        }]
        await create_entities(entities)

        # Try to create the same entity again
        result = await create_entities(entities)
        assert "Entity already exists" in result

        # Verify original entity is unchanged
        graph = await read_graph()
        assert graph["entities"]["test_project"]["observations"] == ["Original project"]


@pytest.mark.asyncio
class TestCreateRelations:
    """Test cases for create_relations function."""

    async def test_create_relation(self, setup_memory, temp_dir):
        """Test creating a relation between entities."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create entities
        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": []
            },
            {
                "name": "component1",
                "entity_type": "component",
                "observations": []
            }
        ]
        await create_entities(entities)

        # Create relation
        relations = [{
            "from_entity": "project1",
            "to_entity": "component1",
            "relation_type": "has_component"
        }]
        result = await create_relations(relations)
        assert "Successfully created relations" in result

        # Verify relation was created
        graph = await read_graph()
        assert len(graph["relations"]) == 1
        assert graph["relations"][0]["from_entity"] == "project1"
        assert graph["relations"][0]["to_entity"] == "component1"
        assert graph["relations"][0]["relation_type"] == "has_component"

    async def test_create_relation_nonexistent_entity(self, setup_memory, temp_dir):
        """Test creating a relation with non-existent entities."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        relations = [{
            "from_entity": "nonexistent1",
            "to_entity": "nonexistent2",
            "relation_type": "has_component"
        }]
        result = await create_relations(relations)
        assert "entities not found" in result


@pytest.mark.asyncio
class TestAddObservations:
    """Test cases for add_observations function."""

    async def test_add_observations(self, setup_memory, temp_dir):
        """Test adding observations to an entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create an entity
        entities = [{
            "name": "test_project",
            "entity_type": "project",
            "observations": ["Original observation"]
        }]
        await create_entities(entities)

        # Add observations
        observations = [{
            "entity_name": "test_project",
            "contents": ["New observation 1", "New observation 2"]
        }]
        result = await add_observations(observations)
        assert "Successfully added observations" in result

        # Verify observations were added
        graph = await read_graph()
        assert "Original observation" in graph["entities"]["test_project"]["observations"]
        assert "New observation 1" in graph["entities"]["test_project"]["observations"]
        assert "New observation 2" in graph["entities"]["test_project"]["observations"]

    async def test_add_observations_nonexistent_entity(self, setup_memory, temp_dir):
        """Test adding observations to a non-existent entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        observations = [{
            "entity_name": "nonexistent",
            "contents": ["New observation"]
        }]
        result = await add_observations(observations)
        assert "Entity not found" in result


@pytest.mark.asyncio
class TestDeleteObservations:
    """Test cases for delete_observations function."""

    async def test_delete_observations(self, setup_memory, temp_dir):
        """Test deleting observations from an entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create an entity with observations
        entities = [{
            "name": "test_project",
            "entity_type": "project",
            "observations": ["Observation 1", "Observation 2"]
        }]
        await create_entities(entities)

        # Delete an observation
        deletions = [{
            "entity_name": "test_project",
            "observation": "Observation 1"
        }]
        result = await delete_observations(deletions)
        assert "Successfully deleted observations" in result

        # Verify observation was deleted
        graph = await read_graph()
        assert "Observation 1" not in graph["entities"]["test_project"]["observations"]
        assert "Observation 2" in graph["entities"]["test_project"]["observations"]

    async def test_delete_observations_nonexistent_entity(self, setup_memory, temp_dir):
        """Test deleting observations from a non-existent entity."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        deletions = [{
            "entity_name": "nonexistent",
            "observation": "Some observation"
        }]
        result = await delete_observations(deletions)
        assert "Entity not found" in result


@pytest.mark.asyncio
class TestDeleteRelations:
    """Test cases for delete_relations function."""

    async def test_delete_relation(self, setup_memory, temp_dir):
        """Test deleting a relation."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create entities and relation
        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": []
            },
            {
                "name": "component1",
                "entity_type": "component",
                "observations": []
            }
        ]
        await create_entities(entities)
        relations = [{
            "from_entity": "project1",
            "to_entity": "component1",
            "relation_type": "has_component"
        }]
        await create_relations(relations)

        # Delete the relation
        result = await delete_relations(relations)
        assert "Successfully deleted relations" in result

        # Verify relation was deleted
        graph = await read_graph()
        assert len(graph["relations"]) == 0


@pytest.mark.asyncio
class TestDeleteEntities:
    """Test cases for delete_entities function."""

    async def test_delete_entity(self, setup_memory, temp_dir):
        """Test deleting an entity and its relations."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # First create entities and relation
        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": []
            },
            {
                "name": "component1",
                "entity_type": "component",
                "observations": []
            }
        ]
        await create_entities(entities)
        relations = [{
            "from_entity": "project1",
            "to_entity": "component1",
            "relation_type": "has_component"
        }]
        await create_relations(relations)

        # Delete an entity
        result = await delete_entities(["project1"])
        assert "Successfully deleted entities" in result

        # Verify entity and its relations were deleted
        graph = await read_graph()
        assert "project1" not in graph["entities"]
        assert len(graph["relations"]) == 0


@pytest.mark.asyncio
class TestSearchNodes:
    """Test cases for search_nodes function."""

    async def test_search_by_name(self, setup_memory, temp_dir):
        """Test searching nodes by name."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # Create test data
        entities = [
            {
                "name": "test_project",
                "entity_type": "project",
                "observations": ["Test project"]
            },
            {
                "name": "other_project",
                "entity_type": "project",
                "observations": ["Other project"]
            }
        ]
        await create_entities(entities)

        # Search for "test"
        result = await search_nodes("test")
        assert "test_project" in result["entities"]
        assert "other_project" not in result["entities"]

    async def test_search_by_observation(self, setup_memory, temp_dir):
        """Test searching nodes by observation content."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        entities = [{
            "name": "test_project",
            "entity_type": "project",
            "observations": ["Contains test observation"]
        }]
        await create_entities(entities)

        result = await search_nodes("test observation")
        assert "test_project" in result["entities"]


@pytest.mark.asyncio
class TestOpenNodes:
    """Test cases for open_nodes function."""

    async def test_open_single_node(self, setup_memory, temp_dir):
        """Test opening a single node."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # Create test data
        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": []
            },
            {
                "name": "project2",
                "entity_type": "project",
                "observations": []
            }
        ]
        await create_entities(entities)

        result = await open_nodes(["project1"])
        assert "project1" in result["entities"]
        assert "project2" not in result["entities"]

    async def test_open_nodes_with_relations(self, setup_memory, temp_dir):
        """Test opening nodes with relations."""
        # Ensure memory file is empty
        memory_path = Path(temp_dir) / MEMORY_FILE_NAME
        with open(memory_path, "w") as f:
            f.write("")  # Clear the file

        # Create test data with relations
        entities = [
            {
                "name": "project1",
                "entity_type": "project",
                "observations": []
            },
            {
                "name": "component1",
                "entity_type": "component",
                "observations": []
            }
        ]
        await create_entities(entities)
        relations = [{
            "from_entity": "project1",
            "to_entity": "component1",
            "relation_type": "has_component"
        }]
        await create_relations(relations)

        result = await open_nodes(["project1"])
        assert "project1" in result["entities"]
        assert len(result["relations"]) == 1
        assert result["relations"][0]["from_entity"] == "project1"
        assert result["relations"][0]["to_entity"] == "component1"


@pytest.mark.asyncio
class TestInitializeGraphFromData:
    """Test cases for initialize_graph_from_data function."""

    async def test_initialize_empty_content(self, setup_memory, temp_dir):
        """Test initializing with empty content."""
        graph = get_graph()
        graph.initialize_graph_from_data("")
        result = await read_graph()
        assert result == {"entities": {}, "relations": []}

    async def test_initialize_with_entities(self, setup_memory, temp_dir):
        """Test initializing with valid entities."""
        content = (
            '{"name": "test_project", "entity_type": "project", "observations": ["Test project"]}\n'
            '{"name": "test_component", "entity_type": "component", "observations": ["Test component"]}'
        )
        graph = get_graph()
        graph.initialize_graph_from_data(content)
        result = await read_graph()
        assert "test_project" in result["entities"]
        assert "test_component" in result["entities"]
        assert result["entities"]["test_project"]["entity_type"] == "project"
        assert result["entities"]["test_component"]["entity_type"] == "component"

    async def test_initialize_with_entities_and_relations(self, setup_memory, temp_dir):
        """Test initializing with valid entities and relations."""
        content = (
            '{"name": "test_project", "entity_type": "project", "observations": ["Test project"]}\n'
            '{"name": "test_component", "entity_type": "component", "observations": ["Test component"]}\n'
            '{"from_entity": "test_project", "to_entity": "test_component", "relation_type": "has_component"}'
        )
        graph = get_graph()
        graph.initialize_graph_from_data(content)
        result = await read_graph()
        assert "test_project" in result["entities"]
        assert "test_component" in result["entities"]
        assert len(result["relations"]) == 1
        assert result["relations"][0]["from_entity"] == "test_project"
        assert result["relations"][0]["to_entity"] == "test_component"
        assert result["relations"][0]["relation_type"] == "has_component"

    async def test_initialize_with_invalid_json(self, setup_memory, temp_dir):
        """Test initializing with invalid JSON lines."""
        content = (
            '{"name": "test_project", "entity_type": "project", "observations": ["Test project"]}\n'
            'invalid json line\n'
            '{"name": "test_component", "entity_type": "component", "observations": ["Test component"]}'
        )
        graph = get_graph()
        graph.initialize_graph_from_data(content)
        result = await read_graph()
        assert "test_project" in result["entities"]
        assert "test_component" in result["entities"]
        assert len(result["entities"]) == 2  # Invalid line should be skipped

    async def test_initialize_with_invalid_data(self, setup_memory, temp_dir):
        """Test initializing with invalid entity/relation data."""
        content = (
            '{"name": "test_project", "entity_type": "invalid_type", "observations": ["Test project"]}\n'
            '{"from_entity": "test_project", "to_entity": "test_component", "relation_type": "invalid_type"}'
        )
        graph = get_graph()
        graph.initialize_graph_from_data(content)
        result = await read_graph()
        assert len(result["entities"]) == 0  # Invalid entity type should be skipped
        assert len(result["relations"]) == 0  # Invalid relation type should be skipped