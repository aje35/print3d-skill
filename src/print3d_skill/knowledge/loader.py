"""Knowledge base loader with AND-filtered context queries.

Discovers YAML files in the knowledge_base package, validates them,
and filters by query context using AND logic with wildcards.
"""

from __future__ import annotations

import importlib.resources

import yaml

from print3d_skill.exceptions import KnowledgeSchemaError
from print3d_skill.knowledge.schemas import validate_knowledge_file
from print3d_skill.models.knowledge import (
    KnowledgeFile,
    KnowledgeMetadata,
    KnowledgeQuery,
)


def _load_all_knowledge_files() -> list[KnowledgeFile]:
    """Discover and load all YAML files from the knowledge_base package."""
    files: list[KnowledgeFile] = []

    package = importlib.resources.files("print3d_skill.knowledge_base")
    _scan_directory(package, files)
    return files


def _scan_directory(
    directory: importlib.resources.abc.Traversable,
    files: list[KnowledgeFile],
) -> None:
    """Recursively scan a directory for YAML knowledge files."""
    for item in directory.iterdir():
        if item.is_dir():
            _scan_directory(item, files)
            continue

        if not item.name.endswith(".yaml"):
            continue

        text = item.read_text(encoding="utf-8")
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise KnowledgeSchemaError(
                f"Failed to parse YAML '{item.name}': {e}"
            ) from e

        validate_knowledge_file(raw, path=item.name)

        metadata_raw = raw["metadata"]
        metadata = KnowledgeMetadata(
            type=metadata_raw["type"],
            topic=metadata_raw.get("topic", ""),
            modes=metadata_raw.get("modes", []),
            materials=metadata_raw.get("materials", []),
            printers=metadata_raw.get("printers", []),
            version=metadata_raw.get("version", "1.0"),
        )

        files.append(KnowledgeFile(
            path=str(item),
            metadata=metadata,
            data=raw["data"],
        ))


def _matches_field(file_values: list[str], query_value: str | None) -> bool:
    """Check if a single query field matches a file's metadata list.

    Rules:
    - If query_value is None → wildcard (always matches)
    - If file_values is empty → matches all (applies to everything)
    - Otherwise → query_value must be in file_values
    """
    if query_value is None:
        return True
    if not file_values:
        return True
    return query_value in file_values


def query_knowledge_files(query: KnowledgeQuery) -> list[KnowledgeFile]:
    """Query the knowledge base with context filters.

    Uses AND matching: all specified fields must match.
    Unspecified fields (None) act as wildcards.
    """
    all_files = _load_all_knowledge_files()
    results: list[KnowledgeFile] = []

    for kf in all_files:
        if not _matches_field(kf.metadata.modes, query.mode):
            continue
        if not _matches_field(kf.metadata.materials, query.material):
            continue
        if not _matches_field(kf.metadata.printers, query.printer):
            continue
        # problem_type maps to metadata.type
        if query.problem_type is not None and kf.metadata.type != query.problem_type:
            continue

        results.append(kf)

    return results
