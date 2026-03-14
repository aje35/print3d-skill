"""Knowledge system data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_KNOWLEDGE_TYPES = (
    "tolerance_table",
    "material_properties",
    "decision_tree",
    "design_rules",
)


@dataclass
class KnowledgeMetadata:
    """Metadata section of a knowledge file, used for query matching."""

    type: str
    topic: str
    modes: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    printers: list[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class KnowledgeFile:
    """A structured knowledge file with metadata for filtering."""

    path: str
    metadata: KnowledgeMetadata
    data: dict[str, Any]


@dataclass
class KnowledgeQuery:
    """Context descriptor for filtering the knowledge base."""

    mode: str | None = None
    material: str | None = None
    printer: str | None = None
    problem_type: str | None = None
