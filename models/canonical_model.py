from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CanonicalReference(BaseModel):
    reference_type: str
    is_forward: bool = True
    target_node_id: str


class CanonicalNode(BaseModel):
    node_id: str
    node_class: str
    browse_name: str
    display_name: str = ""
    description: str = ""
    path: str = ""
    parent_node_id: str | None = None
    data_type: str | None = None
    value_rank: int | None = None
    access_level: str | None = None
    engineering_unit: str | None = None
    references: list[CanonicalReference] = Field(default_factory=list)


class ModelInfo(BaseModel):
    source_file: str
    namespaces: list[str] = Field(default_factory=list)


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_info: ModelInfo
    nodes: list[CanonicalNode]