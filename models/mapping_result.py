from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MappingResult(BaseModel):
    run_info: dict[str, Any]
    node_results: list[dict[str, Any]]
    summary: dict[str, Any]
    review_queue: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)