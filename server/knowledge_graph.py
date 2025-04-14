"""Knowledge Graph implementation for Agentical Framework.

This module provides the core knowledge graph functionality and data structures.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Union

from .schemas import (Entity, EntityCreate, EntityType, GraphData, ObservationAdd,
                      ObservationDelete, Relation, RelationCreate, RelationType)


class MemoryError(Exception):
    """Raised when there is an error performing a memory operation."""
    pass


class KnowledgeGraph:
    """Manages the knowledge graph data structure and persistence."""

    def __init__(self, memory_file_name: str, local_storage: bool = False) -> None:
        """Initialize the knowledge graph.

        Args:
            memory_file_name: Name of the memory file to use.
            local_storage: Whether to use local storage or not.
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

    def initialize_graph_from_data(self, content: str) -> None:
        """Initialize the graph from string content.

        Args:
            content: String containing the graph data in JSON format.
        """
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "name" in data:
                    # Entity
                    self.entities[data["name"]] = Entity(
                        name=data["name"],
                        entity_type=EntityType(data["entity_type"]),
                        observations=data["observations"]
                    )
                elif "from_entity" in data:
                    # Relation
                    self.relations.append(
                        Relation(
                            from_entity=data["from_entity"],
                            to_entity=data["to_entity"],
                            relation_type=RelationType(data["relation_type"])
                        )
                    )
            except json.JSONDecodeError:
                # Skip invalid lines
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
            entity_create = EntityCreate(**entity_data)
            self.entities[entity_data["name"]] = Entity(
                name=entity_create.name,
                entity_type=EntityType(entity_create.entity_type),
                observations=entity_create.observations or []
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
            relation_create = RelationCreate(**relation_data)
            if (
                relation_create.from_entity not in self.entities
                or relation_create.to_entity not in self.entities
            ):
                return f"One or both entities not found: {relation_create.from_entity}, {relation_create.to_entity}"

            self.relations.append(
                Relation(
                    from_entity=relation_create.from_entity,
                    to_entity=relation_create.to_entity,
                    relation_type=RelationType(relation_create.relation_type)
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
            obs_add = ObservationAdd(**obs_data)
            if obs_add.entity_name not in self.entities:
                return f"Entity not found: {obs_add.entity_name}"

            # If all entities exist, add observations
            entity = self.entities[obs_add.entity_name]
            # Ensure we're extending the list, not replacing it
            entity.observations.extend(obs_add.contents)

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
            obs_delete = ObservationDelete(**del_data)
            if obs_delete.entity_name not in self.entities:
                return f"Entity not found: {obs_delete.entity_name}"

            entity = self.entities[obs_delete.entity_name]
            entity.observations = [
                obs for obs in entity.observations if obs != obs_delete.observation
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
            relation_create = RelationCreate(**rel_data)
            if not any(
                r.from_entity == relation_create.from_entity
                and r.to_entity == relation_create.to_entity
                and r.relation_type == RelationType(relation_create.relation_type)
                for r in self.relations
            ):
                return f"Relation not found: {relation_create.from_entity} -> {relation_create.to_entity}"

        # If all relations exist, delete them
        for rel_data in relations:
            relation_create = RelationCreate(**rel_data)
            self.relations = [
                r
                for r in self.relations
                if not (
                    r.from_entity == relation_create.from_entity
                    and r.to_entity == relation_create.to_entity
                    and r.relation_type == RelationType(relation_create.relation_type)
                )
            ]

        self._save_graph()
        return "Successfully deleted relations"

    def read_graph(self) -> Dict[str, Union[Dict[str, Dict], List[Dict]]]:
        """Read the entire knowledge graph.

        Returns:
            Dictionary containing all entities and relations.
        """
        graph_data = GraphData(
            entities={
                name: {
                    "entity_type": entity.entity_type.value,
                    "observations": entity.observations,
                }
                for name, entity in self.entities.items()
            },
            relations=[
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type.value,
                }
                for r in self.relations
            ]
        )
        return graph_data.model_dump()

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

        graph_data = GraphData(
            entities={
                name: {
                    "entity_type": entity.entity_type.value,
                    "observations": entity.observations,
                }
                for name, entity in matching_entities.items()
            },
            relations=[
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type.value,
                }
                for r in matching_relations
            ]
        )
        return graph_data.model_dump()

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

        graph_data = GraphData(
            entities={
                name: {
                    "entity_type": entity.entity_type.value,
                    "observations": entity.observations,
                }
                for name, entity in requested_entities.items()
            },
            relations=[
                {
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "relation_type": r.relation_type.value,
                }
                for r in requested_relations
            ]
        )
        return graph_data.model_dump()