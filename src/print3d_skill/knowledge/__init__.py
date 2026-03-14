"""Knowledge system for on-demand domain knowledge loading.

Public API: query_knowledge()
"""

from __future__ import annotations

from print3d_skill.knowledge.loader import query_knowledge_files
from print3d_skill.models.knowledge import KnowledgeFile, KnowledgeQuery


def query_knowledge(
    mode: str | None = None,
    material: str | None = None,
    printer: str | None = None,
    problem_type: str | None = None,
) -> list[KnowledgeFile]:
    """Query the knowledge base with context filters.

    Uses AND matching: all specified fields must match.
    Unspecified fields (None) act as wildcards.

    A knowledge file matches a field if:
    - The file's metadata list for that field contains the
      query value, OR
    - The file's metadata list is empty (meaning "applies to all")

    Returns matching KnowledgeFile objects with their data.
    Returns an empty list (not an error) when nothing matches.
    """
    query = KnowledgeQuery(
        mode=mode,
        material=material,
        printer=printer,
        problem_type=problem_type,
    )
    return query_knowledge_files(query)
