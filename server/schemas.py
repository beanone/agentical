"""Pydantic schemas for the knowledge graph."""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


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


class Entity(BaseModel):
    """Schema for an entity in the knowledge graph."""
    name: str = Field(..., description="Unique identifier for the entity")
    entity_type: EntityType = Field(..., description="Type classification of the entity")
    observations: List[str] = Field(default_factory=list, description="List of observations about the entity")


class Relation(BaseModel):
    """Schema for a relation between entities in the knowledge graph."""
    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    relation_type: RelationType = Field(..., description="Type of relationship")


class EntityCreate(BaseModel):
    """Schema for creating a new entity."""
    name: str = Field(..., description="Unique identifier for the entity")
    entity_type: str = Field(..., description="Type classification of the entity")
    observations: Optional[List[str]] = Field(default_factory=list, description="List of observations about the entity")


class RelationCreate(BaseModel):
    """Schema for creating a new relation."""
    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Type of relationship")


class ObservationAdd(BaseModel):
    """Schema for adding observations to an entity."""
    entity_name: str = Field(..., description="Name of the entity to add observations to")
    contents: List[str] = Field(..., description="List of observations to add")


class ObservationDelete(BaseModel):
    """Schema for deleting an observation from an entity."""
    entity_name: str = Field(..., description="Name of the entity to delete observation from")
    observation: str = Field(..., description="Observation to delete")


class GraphData(BaseModel):
    """Schema for the complete graph data."""
    entities: Dict[str, Dict[str, Union[str, List[str]]]] = Field(
        default_factory=dict,
        description="Dictionary of entities with their types and observations"
    )
    relations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of relations between entities"
    )