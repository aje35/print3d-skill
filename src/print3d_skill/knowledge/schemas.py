"""Knowledge file schema validation.

Validates YAML structure: must have metadata and data top-level keys,
metadata fields must conform to expected types and enums.
"""

from __future__ import annotations

from typing import Any

from print3d_skill.exceptions import KnowledgeSchemaError
from print3d_skill.models.knowledge import VALID_KNOWLEDGE_TYPES


def validate_knowledge_file(data: dict[str, Any], path: str = "") -> None:
    """Validate a parsed YAML knowledge file.

    Raises KnowledgeSchemaError on invalid structure.
    """
    prefix = f"'{path}': " if path else ""

    if not isinstance(data, dict):
        raise KnowledgeSchemaError(f"{prefix}Knowledge file must be a YAML mapping")

    if "metadata" not in data:
        raise KnowledgeSchemaError(f"{prefix}Missing required 'metadata' section")

    if "data" not in data:
        raise KnowledgeSchemaError(f"{prefix}Missing required 'data' section")

    metadata = data["metadata"]
    if not isinstance(metadata, dict):
        raise KnowledgeSchemaError(f"{prefix}'metadata' must be a mapping")

    # Required metadata fields
    if "type" not in metadata:
        raise KnowledgeSchemaError(f"{prefix}metadata missing required field 'type'")

    if metadata["type"] not in VALID_KNOWLEDGE_TYPES:
        raise KnowledgeSchemaError(
            f"{prefix}metadata.type '{metadata['type']}' not valid. "
            f"Must be one of: {', '.join(VALID_KNOWLEDGE_TYPES)}"
        )

    if "topic" not in metadata:
        raise KnowledgeSchemaError(f"{prefix}metadata missing required field 'topic'")

    # List fields must be lists
    for field_name in ("modes", "materials", "printers"):
        if field_name in metadata and not isinstance(metadata[field_name], list):
            raise KnowledgeSchemaError(
                f"{prefix}metadata.{field_name} must be a list"
            )

    # Version must be a string
    if "version" in metadata and not isinstance(metadata["version"], str):
        raise KnowledgeSchemaError(f"{prefix}metadata.version must be a string")
