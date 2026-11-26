from typing import List, Literal
from pydantic import BaseModel, Field


class Entity(BaseModel):
    id: str = Field(..., description="Unique canonical identifier, e.g., 'mohankumard18', 'fastapi', 'issue-42'")
    label: Literal["Developer", "Repository", "Technology", "Issue", "Commit"] = Field(
        ..., description="Node label in the Developer Memory Graph"
    )
    name: str = Field(..., description="Human-readable display name or title")
    summary: str = Field(..., description="Concise context about this entity from the engineering log")


class Relationship(BaseModel):
    source_id: str = Field(..., description="Canonical ID of the source entity")
    target_id: str = Field(..., description="Canonical ID of the target entity")
    relation_type: Literal[
        "CONTRIBUTED_TO",
        "USES_TECH",
        "RESOLVED",
        "AUTHORED",
        "DEPENDS_ON",
        "REPORTED",
    ] = Field(..., description="Directed relationship type connecting source to target")
    context: str = Field(..., description="Brief description of why this relationship exists")


class ExtractedMemoryGraph(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)