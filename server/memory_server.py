"""Memory Tool for Agentical Framework.

This module provides MCP-compliant tools for knowledge graph memory operations.
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from mcp.server.fastmcp import FastMCP

from .knowledge_graph import KnowledgeGraph

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("memory")

# Constants
MEMORY_FILE_PATH = os.getenv("MEMORY_FILE_PATH", ".")
MEMORY_FILE_NAME = os.getenv("MEMORY_FILE_NAME", "memory.json")
LOCAL_STORAGE = os.getenv("LOCAL_STORAGE", "false").lower() == "true"

# Global graph instance
_graph: Optional[KnowledgeGraph] = None

def get_graph() -> KnowledgeGraph:
    """Get the global graph instance."""
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph(MEMORY_FILE_NAME, LOCAL_STORAGE)
    return _graph


def clear_graph() -> None:
    """Clear the global graph instance."""
    global _graph
    if _graph is not None:
        storage_path = _graph.storage_path
        memory_file_name = _graph.memory_file_name
        # Clear the file
        if storage_path.exists():
            with open(storage_path, "w") as f:
                f.write("")
                f.flush()
                os.fsync(f.fileno())
        # Create a new graph instance with the same file path
        _graph = KnowledgeGraph(memory_file_name, LOCAL_STORAGE)
        _graph.storage_path = storage_path
        # Ensure the graph is properly initialized
        _graph._load_graph()


class MemoryError(Exception):
    """Raised when there is an error performing a memory operation."""

    pass


class EntityType(str, Enum):
    """Valid entity types in the knowledge graph."""

    PROJECT = "project"
    COMPONENT = "component"
    ISSUE = "issue"
    STATUS = "status"
    SESSION = "session"
    ADAPTER = "adapter"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    META = "meta"
    RULE = "rule"


class RelationType(str, Enum):
    """Valid relation types in the knowledge graph."""

    HAS_COMPONENT = "has_component"
    HAS_ISSUE = "has_issue"
    PART_OF = "part_of"
    USES = "uses"
    CONFIGURED_BY = "configured_by"
    RELATED_TO = "related_to"
    AFFECTS = "affects"
    IMPLEMENTS = "implements"
    DOCUMENTS = "documents"
    REFERENCES = "references"
    ADDRESSES = "addresses"
    DISCUSSES = "discusses"


@dataclass
class Entity:
    """Represents an entity in the knowledge graph.

    Attributes:
        name: Unique identifier for the entity
        entity_type: Type classification of the entity
        observations: List of observations about the entity
    """

    name: str
    entity_type: EntityType
    observations: List[str]


@dataclass
class Relation:
    """Represents a relation between entities in the knowledge graph.

    Attributes:
        from_entity: Source entity name
        to_entity: Target entity name
        relation_type: Type of relationship
    """

    from_entity: str
    to_entity: str
    relation_type: RelationType


class KnowledgeGraph:
    """Manages the knowledge graph data structure and persistence."""

    def __init__(self, memory_file_name: str = MEMORY_FILE_NAME, local_storage: bool = LOCAL_STORAGE) -> None:
        """Initialize the knowledge graph.

        Args:
            memory_file_name: Name of the memory file to use.
            local_storage: Whether to use local storage.
        """
        self.memory_file_name = memory_file_name
        self.storage_path = (
            Path(os.getenv("MEMORY_FILE_PATH", ".")) / memory_file_name
            if not local_storage
            else Path.cwd() / memory_file_name
        )
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self._load_graph()

    def clear(self) -> None:
        """Clear the graph state."""
        self.entities = {}
        self.relations = []

    def _load_graph(self) -> None:
        """Load the knowledge graph from storage."""
        # Clear existing state before loading
        self.entities = {}
        self.relations = []

        try:
            if not self.storage_path.exists():
                # Create parent directory if it doesn't exist
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                # Create empty graph file
                with open(self.storage_path, "w") as f:
                    f.write("")
                    f.flush()
                    os.fsync(f.fileno())
                return

            # Read the file line by line
            with open(self.storage_path, "r") as f:
                content = f.read().strip()
                if not content:  # Empty file
                    return
                self.initialize_graph_from_data(content)
        except (json.JSONDecodeError, OSError) as e:
            # If file is corrupted or there's an IO error, start fresh
            self.entities = {}
            self.relations = []
            if self.storage_path.exists():
                with open(self.storage_path, "w") as f:
                    f.write("")
                    f.flush()
                    os.fsync(f.fileno())

    def initialize_graph_from_data(self, content):
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "name" in data:
                    # Entity
                    try:
                        self.entities[data["name"]] = Entity(
                            name=data["name"],
                            entity_type=EntityType(data["entity_type"]),
                            observations=data["observations"],
                        )
                    except ValueError:
                        # Log warning for invalid entity type
                        logger.warning(
                            "Invalid entity type '%s' for entity '%s'. Skipping entity.",
                            data.get("entity_type", "UNKNOWN"),
                            data.get("name", "UNKNOWN"),
                        )
                        continue
                elif "from_entity" in data:
                    # Relation
                    try:
                        self.relations.append(
                            Relation(
                                from_entity=data["from_entity"],
                                to_entity=data["to_entity"],
                                relation_type=RelationType(data["relation_type"]),
                            )
                        )
                    except ValueError:
                        # Log warning for invalid relation type
                        logger.warning(
                            "Invalid relation type '%s' between '%s' and '%s'. Skipping relation.",
                            data.get("relation_type", "UNKNOWN"),
                            data.get("from_entity", "UNKNOWN"),
                            data.get("to_entity", "UNKNOWN"),
                        )
                        continue
            except json.JSONDecodeError:
                # Log warning for invalid JSON
                logger.warning("Invalid JSON line encountered. Skipping line: %s", line[:100])
                continue

    def _save_graph(self) -> None:
        """Save the knowledge graph to storage."""
        # Create parent directory if it doesn't exist
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(self.storage_path, "w") as f:
            # Write entities
            for entity in self.entities.values():
                json.dump(
                    {
                        "name": entity.name,
                        "entity_type": entity.entity_type.value,
                        "observations": entity.observations,
                    },
                    f,
                )
                f.write("\n")

            # Write relations
            for relation in self.relations:
                json.dump(
                    {
                        "from_entity": relation.from_entity,
                        "to_entity": relation.to_entity,
                        "relation_type": relation.relation_type.value,
                    },
                    f,
                )
                f.write("\n")

            # Ensure the file is flushed and synced
            f.flush()
            os.fsync(f.fileno())

    def create_entities(self, entities: List[Dict[str, Union[str, List[str]]]]) -> str:
        """Create new entities in the graph.

        Args:
            entities: List of entity dictionaries.

        Returns:
            Success message or error string.
        """
        # First check if any entities already exist
        for entity_data in entities:
            if entity_data["name"] in self.entities:
                return f"Entity already exists: {entity_data['name']}"

        # If all entities are new, create them
        for entity_data in entities:
            self.entities[entity_data["name"]] = Entity(
                name=entity_data["name"],
                entity_type=EntityType(entity_data["entity_type"]),
                observations=entity_data.get("observations", []),
            )

        self._save_graph()
        return "Successfully created entities"

    def create_relations(self, relations: List[Dict[str, str]]) -> str:
        """Create new relations between entities.

        Args:
            relations: List of relation dictionaries.

        Returns:
            Success message or error string.
        """
        for relation_data in relations:
            if (
                relation_data["from_entity"] not in self.entities
                or relation_data["to_entity"] not in self.entities
            ):
                return f"One or both entities not found: {relation_data['from_entity']}, {relation_data['to_entity']}"

            self.relations.append(
                Relation(
                    from_entity=relation_data["from_entity"],
                    to_entity=relation_data["to_entity"],
                    relation_type=RelationType(relation_data["relation_type"]),
                )
            )

        self._save_graph()
        return "Successfully created relations"

    def add_observations(self, observations: List[Dict[str, Union[str, List[str]]]]) -> str:
        """Add observations to existing entities.

        Args:
            observations: List of observation dictionaries.

        Returns:
            Success message or error string.
        """
        # First check if all entities exist
        for obs_data in observations:
            if obs_data["entity_name"] not in self.entities:
                return f"Entity not found: {obs_data['entity_name']}"

        # If all entities exist, add observations
        for obs_data in observations:
            entity = self.entities[obs_data["entity_name"]]
            # Ensure we're extending the list, not replacing it
            entity.observations.extend(obs_data["contents"])

        self._save_graph()
        return "Successfully added observations"

    def delete_entities(self, entity_names: List[str]) -> str:
        """Delete entities and their relations.

        Args:
            entity_names: List of entity names to delete.

        Returns:
            Success message or error string.
        """
        for name in entity_names:
            if name in self.entities:
                del self.entities[name]
                # Remove related relations
                self.relations = [
                    r
                    for r in self.relations
                    if r.from_entity != name and r.to_entity != name
                ]

        self._save_graph()
        return "Successfully deleted entities"

    def delete_observations(self, deletions: List[Dict[str, str]]) -> str:
        """Delete specific observations from entities.

        Args:
            deletions: List of deletion dictionaries.

        Returns:
            Success message or error string.
        """
        for del_data in deletions:
            if del_data["entity_name"] not in self.entities:
                return f"Entity not found: {del_data['entity_name']}"

            entity = self.entities[del_data["entity_name"]]
            entity.observations = [
                obs for obs in entity.observations if obs != del_data["observation"]
            ]

        self._save_graph()
        return "Successfully deleted observations"

    def delete_relations(self, relations: List[Dict[str, str]]) -> str:
        """Delete specific relations from the graph.

        Args:
            relations: List of relation dictionaries.

        Returns:
            Success message or error string.
        """
        # First check if all relations exist
        for rel_data in relations:
            if not any(
                r.from_entity == rel_data["from_entity"]
                and r.to_entity == rel_data["to_entity"]
                and r.relation_type == RelationType(rel_data["relation_type"])
                for r in self.relations
            ):
                return f"Relation not found: {rel_data['from_entity']} -> {rel_data['to_entity']}"

        # If all relations exist, delete them
        for rel_data in relations:
            self.relations = [
                r
                for r in self.relations
                if not (
                    r.from_entity == rel_data["from_entity"]
                    and r.to_entity == rel_data["to_entity"]
                    and r.relation_type == RelationType(rel_data["relation_type"])
                )
            ]

        self._save_graph()
        return "Successfully deleted relations"

    def read_graph(self) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
        """Read the entire knowledge graph.

        Returns:
            Dictionary containing all entities and relations.
        """
        return {
            "entities": {
                name: {
                    "entity_type": entity.entity_type,
                    "observations": entity.observations,
                }
                for name, entity in self.entities.items()
            },
            "relations": [
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type,
                }
                for r in self.relations
            ],
        }

    def search_nodes(self, query: str) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
        """Search for nodes based on query.

        Args:
            query: Search query string.

        Returns:
            Dictionary containing matching entities and their relations.
        """
        query = query.lower()
        matching_entities = {}

        # Search in entity names and types
        for name, entity in self.entities.items():
            if query in name.lower() or query in entity.entity_type.value.lower():
                matching_entities[name] = entity
                continue

            # Search in observations
            for obs in entity.observations:
                if query in obs.lower():
                    matching_entities[name] = entity
                    break

        # Get relations for matching entities
        matching_relations = [
            r
            for r in self.relations
            if r.from_entity in matching_entities or r.to_entity in matching_entities
        ]

        return {
            "entities": {
                name: {
                    "entity_type": entity.entity_type,
                    "observations": entity.observations,
                }
                for name, entity in matching_entities.items()
            },
            "relations": [
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type,
                }
                for r in matching_relations
            ],
        }

    def open_nodes(self, names: List[str]) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
        """Open specific nodes by name.

        Args:
            names: List of entity names to retrieve.

        Returns:
            Dictionary containing requested entities and their relations.
        """
        requested_entities = {
            name: self.entities[name]
            for name in names
            if name in self.entities
        }

        requested_relations = [
            r
            for r in self.relations
            if r.from_entity in requested_entities or r.to_entity in requested_entities
        ]

        return {
            "entities": {
                name: {
                    "entity_type": entity.entity_type,
                    "observations": entity.observations,
                }
                for name, entity in requested_entities.items()
            },
            "relations": [
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type,
                }
                for r in requested_relations
            ],
        }


@mcp.tool()
async def create_entities(entities: List[Dict[str, Union[str, List[str]]]]) -> str:
    """Create new entities in the graph.

    Args:
        entities: List of entity dictionaries.

    Returns:
        Success message or error string.
    """
    return get_graph().create_entities(entities)


@mcp.tool()
async def create_relations(relations: List[Dict[str, str]]) -> str:
    """Create new relations between entities.

    Args:
        relations: List of relation dictionaries.

    Returns:
        Success message or error string.
    """
    return get_graph().create_relations(relations)


@mcp.tool()
async def add_observations(observations: List[Dict[str, Union[str, List[str]]]]) -> str:
    """Add observations to existing entities.

    Args:
        observations: List of observation dictionaries.

    Returns:
        Success message or error string.
    """
    return get_graph().add_observations(observations)


@mcp.tool()
async def delete_entities(entity_names: List[str]) -> str:
    """Delete entities and their relations.

    Args:
        entity_names: List of entity names to delete.

    Returns:
        Success message or error string.
    """
    return get_graph().delete_entities(entity_names)


@mcp.tool()
async def delete_observations(deletions: List[Dict[str, str]]) -> str:
    """Delete observations from entities.

    Args:
        deletions: List of deletion dictionaries.

    Returns:
        Success message or error string.
    """
    return get_graph().delete_observations(deletions)


@mcp.tool()
async def delete_relations(relations: List[Dict[str, str]]) -> str:
    """Delete relations between entities.

    Args:
        relations: List of relation dictionaries.

    Returns:
        Success message or error string.
    """
    return get_graph().delete_relations(relations)


@mcp.tool()
async def read_graph() -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
    """Read the current state of the graph.

    Returns:
        Dictionary containing entities and relations.
    """
    return get_graph().read_graph()


@mcp.tool()
async def search_nodes(query: str) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
    """Search for nodes by name or observation content.

    Args:
        query: Search string.

    Returns:
        Dictionary containing matching entities and their relations.
    """
    return get_graph().search_nodes(query)


@mcp.tool()
async def open_nodes(names: List[str]) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
    """Open specific nodes and their relations.

    Args:
        names: List of entity names to open.

    Returns:
        Dictionary containing specified entities and their relations.
    """
    return get_graph().open_nodes(names)


if __name__ == "__main__":
    mcp.run(transport="stdio")