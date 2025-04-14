"""Unit tests for the knowledge graph implementation."""

import json
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import mock_open, patch

import pytest

from server.knowledge_graph import (Entity, EntityType,
                                    KnowledgeGraph, MemoryError,
                                    Relation, RelationType)

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    test_file = tmp_path / "test_memory.json"
    return test_file

@pytest.fixture
def empty_graph(temp_file):
    """Create an empty graph instance."""
    return KnowledgeGraph(str(temp_file), local_storage=True)

@pytest.fixture
def sample_entity() -> Dict:
    """Create a sample entity dictionary."""
    return {
        "name": "test_entity",
        "entity_type": "project",
        "observations": ["test observation"]
    }

@pytest.fixture
def sample_relation() -> Dict:
    """Create a sample relation dictionary."""
    return {
        "from_entity": "test_entity",
        "to_entity": "test_entity2",
        "relation_type": "has_component"
    }

def test_entity_creation():
    """Test Entity dataclass creation."""
    entity = Entity(
        name="test",
        entity_type=EntityType.PROJECT,
        observations=["test observation"]
    )
    assert entity.name == "test"
    assert entity.entity_type == EntityType.PROJECT
    assert entity.observations == ["test observation"]

def test_relation_creation():
    """Test Relation dataclass creation."""
    relation = Relation(
        from_entity="test1",
        to_entity="test2",
        relation_type=RelationType.HAS_COMPONENT
    )
    assert relation.from_entity == "test1"
    assert relation.to_entity == "test2"
    assert relation.relation_type == RelationType.HAS_COMPONENT

def test_memory_error():
    """Test MemoryError exception."""
    with pytest.raises(MemoryError):
        raise MemoryError("test error")

def test_entity_type_enum():
    """Test EntityType enum values."""
    assert EntityType.PROJECT.value == "project"
    assert EntityType.COMPONENT.value == "component"
    assert len(EntityType) == 10  # Verify all types are present

def test_relation_type_enum():
    """Test RelationType enum values."""
    assert RelationType.HAS_COMPONENT.value == "has_component"
    assert RelationType.HAS_ISSUE.value == "has_issue"
    assert len(RelationType) == 12  # Verify all types are present

def test_graph_initialization(temp_file):
    """Test graph initialization."""
    graph = KnowledgeGraph(str(temp_file), local_storage=True)
    assert graph.memory_file_name == str(temp_file)
    assert graph.storage_path == temp_file
    assert isinstance(graph.entities, dict)
    assert isinstance(graph.relations, list)
    assert len(graph.entities) == 0
    assert len(graph.relations) == 0

def test_graph_clear(empty_graph, sample_entity):
    """Test clearing the graph."""
    empty_graph.create_entities([sample_entity])
    assert len(empty_graph.entities) == 1

    empty_graph.clear()
    assert len(empty_graph.entities) == 0
    assert len(empty_graph.relations) == 0

def test_create_entities(empty_graph, sample_entity):
    """Test entity creation."""
    result = empty_graph.create_entities([sample_entity])
    assert result == "Successfully created entities"
    assert len(empty_graph.entities) == 1
    assert empty_graph.entities["test_entity"].name == "test_entity"

def test_create_duplicate_entity(empty_graph, sample_entity):
    """Test creating duplicate entity."""
    empty_graph.create_entities([sample_entity])
    result = empty_graph.create_entities([sample_entity])
    assert result == "Entity already exists: test_entity"

def test_create_relations(empty_graph, sample_entity, sample_relation):
    """Test relation creation."""
    # Create required entities first
    empty_graph.create_entities([
        sample_entity,
        {**sample_entity, "name": "test_entity2"}
    ])

    result = empty_graph.create_relations([sample_relation])
    assert result == "Successfully created relations"
    assert len(empty_graph.relations) == 1

def test_create_invalid_relation(empty_graph, sample_relation):
    """Test creating relation with non-existent entities."""
    result = empty_graph.create_relations([sample_relation])
    assert result.startswith("One or both entities not found")

def test_add_observations(empty_graph, sample_entity):
    """Test adding observations to entities."""
    empty_graph.create_entities([sample_entity])

    observations = [{
        "entity_name": "test_entity",
        "contents": ["new observation"]
    }]

    result = empty_graph.add_observations(observations)
    assert result == "Successfully added observations"
    assert len(empty_graph.entities["test_entity"].observations) == 2

def test_add_observations_invalid_entity(empty_graph):
    """Test adding observations to non-existent entity."""
    observations = [{
        "entity_name": "non_existent",
        "contents": ["test"]
    }]

    result = empty_graph.add_observations(observations)
    assert result == "Entity not found: non_existent"

def test_delete_entities(empty_graph, sample_entity, sample_relation):
    """Test deleting entities."""
    # Setup test data
    empty_graph.create_entities([
        sample_entity,
        {**sample_entity, "name": "test_entity2"}
    ])
    empty_graph.create_relations([sample_relation])

    result = empty_graph.delete_entities(["test_entity"])
    assert result == "Successfully deleted entities"
    assert "test_entity" not in empty_graph.entities
    assert len(empty_graph.relations) == 0

def test_delete_observations(empty_graph, sample_entity):
    """Test deleting observations."""
    empty_graph.create_entities([sample_entity])

    deletions = [{
        "entity_name": "test_entity",
        "observation": "test observation"
    }]

    result = empty_graph.delete_observations(deletions)
    assert result == "Successfully deleted observations"
    assert len(empty_graph.entities["test_entity"].observations) == 0

def test_delete_observations_invalid_entity(empty_graph):
    """Test deleting observations from non-existent entity."""
    deletions = [{
        "entity_name": "non_existent",
        "observation": "test"
    }]

    result = empty_graph.delete_observations(deletions)
    assert result == "Entity not found: non_existent"

def test_delete_relations(empty_graph, sample_entity, sample_relation):
    """Test deleting relations."""
    # Setup test data
    empty_graph.create_entities([
        sample_entity,
        {**sample_entity, "name": "test_entity2"}
    ])
    empty_graph.create_relations([sample_relation])

    result = empty_graph.delete_relations([sample_relation])
    assert result == "Successfully deleted relations"
    assert len(empty_graph.relations) == 0

def test_delete_nonexistent_relation(empty_graph, sample_relation):
    """Test deleting non-existent relation."""
    result = empty_graph.delete_relations([sample_relation])
    assert result.startswith("Relation not found")

def test_read_graph(empty_graph, sample_entity, sample_relation):
    """Test reading the entire graph."""
    # Setup test data
    empty_graph.create_entities([
        sample_entity,
        {**sample_entity, "name": "test_entity2"}
    ])
    empty_graph.create_relations([sample_relation])

    result = empty_graph.read_graph()
    assert "entities" in result
    assert "relations" in result
    assert len(result["entities"]) == 2
    assert len(result["relations"]) == 1

def test_search_nodes(empty_graph, sample_entity):
    """Test searching nodes."""
    empty_graph.create_entities([sample_entity])

    # Test searching by name
    result = empty_graph.search_nodes("test_entity")
    assert len(result["entities"]) == 1

    # Test searching by type
    result = empty_graph.search_nodes("project")
    assert len(result["entities"]) == 1

    # Test searching by observation
    result = empty_graph.search_nodes("observation")
    assert len(result["entities"]) == 1

    # Test searching with no matches
    result = empty_graph.search_nodes("nonexistent")
    assert len(result["entities"]) == 0

def test_open_nodes(empty_graph, sample_entity):
    """Test opening specific nodes."""
    empty_graph.create_entities([sample_entity])

    result = empty_graph.open_nodes(["test_entity"])
    assert len(result["entities"]) == 1
    assert "test_entity" in result["entities"]

def test_open_nonexistent_nodes(empty_graph):
    """Test opening non-existent nodes."""
    result = empty_graph.open_nodes(["nonexistent"])
    assert len(result["entities"]) == 0

def test_initialize_graph_from_data(empty_graph):
    """Test initializing graph from data."""
    content = (
        '{"name": "test", "entity_type": "project", "observations": []}\n'
        '{"from_entity": "test", "to_entity": "test2", "relation_type": "has_component"}\n'
        'invalid json line\n'
    )

    empty_graph.initialize_graph_from_data(content)
    assert len(empty_graph.entities) == 1
    assert len(empty_graph.relations) == 1

def test_load_graph_file_corruption(temp_file):
    """Test handling of corrupted graph file."""
    # Create corrupted file
    with open(temp_file, 'w') as f:
        f.write('invalid json')

    graph = KnowledgeGraph(str(temp_file), local_storage=True)
    assert len(graph.entities) == 0
    assert len(graph.relations) == 0

def test_save_graph(empty_graph, sample_entity, sample_relation):
    """Test saving graph to file."""
    # Setup test data
    empty_graph.create_entities([
        sample_entity,
        {**sample_entity, "name": "test_entity2"}
    ])
    empty_graph.create_relations([sample_relation])

    # Force a save
    empty_graph._save_graph()

    # Verify file contents
    with open(empty_graph.storage_path, 'r') as f:
        content = f.read().strip().split('\n')
        assert len(content) == 3  # 2 entities + 1 relation

def test_graph_with_env_path():
    """Test graph initialization with environment path."""
    with patch.dict(os.environ, {'MEMORY_FILE_PATH': '/test/path'}):
        graph = KnowledgeGraph("test.json", local_storage=False)
        assert str(graph.storage_path) == "/test/path/test.json"