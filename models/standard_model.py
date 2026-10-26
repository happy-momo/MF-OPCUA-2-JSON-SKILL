from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StandardVariable(BaseModel):
    source_node_id: str
    code: str | None = None
    name: str
    value_type: str | None = None
    unit: str | None = None
    confidence: float = 0.0


class StandardEquipment(BaseModel):
    source_node_id: str
    code: str | None = None
    name: str
    equipment_type: str | None = None
    variables: list[StandardVariable] = Field(default_factory=list)


class StandardHierarchyNode(BaseModel):
    level: Literal["Site", "Area", "Line", "Equipment"]
    source_node_id: str | None = None
    code: str | None = None
    name: str
    synthetic: bool = False
    fallback_reason: str | None = None
    children: list["StandardHierarchyNode"] = Field(default_factory=list)
    equipment: StandardEquipment | None = None


class StandardModel(BaseModel):
    standard_id: str
    bundle_version: str
    sites: list[StandardHierarchyNode] = Field(default_factory=list)
    unassigned_equipment: list[StandardEquipment] = Field(default_factory=list)
    unassigned_variables: list[StandardVariable] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)