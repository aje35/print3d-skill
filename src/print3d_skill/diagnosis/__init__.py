"""Print failure diagnosis engine.

Accepts pre-identified defect categories from the AI agent,
walks diagnostic decision trees, and generates specific
actionable fix recommendations.
"""

from __future__ import annotations

from print3d_skill.diagnosis.engine import DiagnosisEngine
from print3d_skill.diagnosis.models import (
    DiagnosisResult,
    DiagnosticContext,
    PrintDefect,
    PrintDefectCategory,
    PrintDefectSeverity,
    Recommendation,
    RootCause,
)


def diagnose_print(
    defects: list[PrintDefect],
    context: DiagnosticContext | None = None,
) -> DiagnosisResult:
    """Diagnose print failures and generate fix recommendations.

    Args:
        defects: Pre-identified defects from agent's photo analysis.
            Must contain at least one defect.
        context: User's setup information (printer, material, settings).
            If None, general diagnosis without context-specific ranking.

    Returns:
        DiagnosisResult with populated root_causes, recommendations,
        conflicts, and context_quality.

    Raises:
        ValueError: If defects list is empty.
        DiagnosisError: If knowledge base is missing or corrupted.
    """
    if not defects:
        raise ValueError("At least one defect must be provided for diagnosis")

    ctx = context or DiagnosticContext()
    engine = DiagnosisEngine()

    # Derive context fields (printer_family, extruder_type) from printer_model
    ctx = engine.derive_context(ctx)
    context_quality = engine.assess_context_quality(ctx)

    # Enrich defects with severity from knowledge base
    enriched = engine.enrich_defects(defects)

    # Walk decision trees to find root causes
    all_causes: list[RootCause] = []
    for defect in enriched:
        causes = engine.walk_decision_tree(defect, ctx)
        all_causes.extend(causes)

    # Generate recommendations from root causes
    recommendations = engine.generate_recommendations(all_causes, ctx, enriched)

    # Sort recommendations and detect conflicts
    sorted_recs = engine.sort_recommendations(
        recommendations, enriched, all_causes
    )
    conflicts = engine.detect_conflicts(sorted_recs)

    return DiagnosisResult(
        defects=enriched,
        context=ctx,
        root_causes=all_causes,
        recommendations=sorted_recs,
        conflicts=conflicts,
        context_quality=context_quality,
    )


__all__ = [
    "DiagnosisEngine",
    "DiagnosisResult",
    "DiagnosticContext",
    "PrintDefect",
    "PrintDefectCategory",
    "PrintDefectSeverity",
    "Recommendation",
    "RootCause",
    "diagnose_print",
]
