"""Diagnosis engine: decision tree walking and recommendation generation.

Loads diagnostic knowledge (defect guides, decision trees, material
failure modes, printer troubleshooting data) via the knowledge system,
then walks decision trees to produce ranked root causes and specific
fix recommendations.
"""

from __future__ import annotations

from typing import Any

from print3d_skill.diagnosis.models import (
    DiagnosticContext,
    PrintDefect,
    PrintDefectCategory,
    PrintDefectSeverity,
    Recommendation,
    RootCause,
)
from print3d_skill.exceptions import DiagnosisError
from print3d_skill.knowledge import query_knowledge

# Mapping from printer model substrings to family and extruder type
_PRINTER_FAMILY_MAP: dict[str, tuple[str, str]] = {
    "bambu": ("bambu", "direct_drive"),
    "p1s": ("bambu", "direct_drive"),
    "p1p": ("bambu", "direct_drive"),
    "x1c": ("bambu", "direct_drive"),
    "x1": ("bambu", "direct_drive"),
    "a1": ("bambu", "direct_drive"),
    "prusa": ("prusa", "direct_drive"),
    "mk3": ("prusa", "direct_drive"),
    "mk4": ("prusa", "direct_drive"),
    "mini": ("prusa", "direct_drive"),
    "creality": ("creality", "bowden"),
    "ender": ("creality", "bowden"),
    "ender 3": ("creality", "bowden"),
    "k1": ("creality", "direct_drive"),
    "cr-10": ("creality", "bowden"),
}

# Settings that conflict when adjusted in opposite directions
_CONFLICT_PAIRS: list[tuple[str, str, str]] = [
    # (setting, direction1_keyword, direction2_keyword)
    ("first_layer_squish", "increase", "decrease"),
    ("z_offset", "increase", "decrease"),
    ("bed_temperature", "increase", "decrease"),
    ("print_speed", "increase", "decrease"),
    ("retraction_distance", "increase", "decrease"),
    ("hotend_temperature", "increase", "decrease"),
    ("cooling_fan_speed", "increase", "decrease"),
]

_SEVERITY_ORDER = {
    PrintDefectSeverity.print_stopping: 0,
    PrintDefectSeverity.functional: 1,
    PrintDefectSeverity.cosmetic: 2,
}

_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}
_DIFFICULTY_ORDER = {"easy": 0, "moderate": 1, "hard": 2}


class DiagnosisEngine:
    """Walks diagnostic knowledge to produce root causes and recommendations."""

    def __init__(self) -> None:
        self._defect_guides: dict[str, Any] | None = None
        self._decision_trees: dict[str, Any] | None = None
        self._material_data: dict[str, Any] | None = None
        self._printer_data: dict[str, Any] | None = None

    # ── Knowledge loading ──────────────────────────────────────────

    def load_defect_guides(self) -> dict[str, Any]:
        """Load defect guide knowledge (type=defect_guide, mode=diagnose)."""
        if self._defect_guides is not None:
            return self._defect_guides

        results = query_knowledge(mode="diagnose", problem_type="defect_guide")
        if not results:
            raise DiagnosisError(
                "No defect guide knowledge found. "
                "Ensure knowledge_base/diagnose/defect_guides.yaml exists."
            )
        # Merge all guide files (typically one)
        categories: dict[str, Any] = {}
        for kf in results:
            cats = kf.data.get("categories", {})
            categories.update(cats)

        self._defect_guides = categories
        return categories

    def load_decision_trees(self) -> dict[str, Any]:
        """Load decision tree knowledge (type=decision_tree, mode=diagnose)."""
        if self._decision_trees is not None:
            return self._decision_trees

        results = query_knowledge(mode="diagnose", problem_type="decision_tree")
        trees: dict[str, Any] = {}
        for kf in results:
            file_trees = kf.data.get("trees", {})
            trees.update(file_trees)
        self._decision_trees = trees
        return trees

    def load_material_data(self) -> dict[str, Any]:
        """Load material failure mode knowledge."""
        if self._material_data is not None:
            return self._material_data

        results = query_knowledge(mode="diagnose", problem_type="material_properties")
        materials: dict[str, Any] = {}
        for kf in results:
            mats = kf.data.get("materials", {})
            if isinstance(mats, list):
                for m in mats:
                    key = m.get("name", "").upper()
                    if key:
                        materials[key] = m
            elif isinstance(mats, dict):
                materials.update(mats)
        self._material_data = materials
        return materials

    def load_printer_data(self) -> dict[str, Any]:
        """Load printer troubleshooting knowledge."""
        if self._printer_data is not None:
            return self._printer_data

        results = query_knowledge(
            mode="diagnose", problem_type="printer_capabilities"
        )
        families: dict[str, Any] = {}
        for kf in results:
            fams = kf.data.get("printer_families", {})
            if isinstance(fams, list):
                for f in fams:
                    key = f.get("name", "").lower().split()[0]
                    if key:
                        families[key] = f
            elif isinstance(fams, dict):
                families.update(fams)
        self._printer_data = families
        return families

    # ── Context enrichment ─────────────────────────────────────────

    def derive_context(self, context: DiagnosticContext) -> DiagnosticContext:
        """Fill in derived fields (printer_family, extruder_type) from printer_model."""
        if context.printer_model and not context.printer_family:
            model_lower = context.printer_model.lower()
            for key, (family, ext_type) in _PRINTER_FAMILY_MAP.items():
                if key in model_lower:
                    context.printer_family = family
                    if not context.extruder_type:
                        context.extruder_type = ext_type
                    break
        return context

    def assess_context_quality(self, context: DiagnosticContext) -> str:
        """Determine context quality: 'full', 'partial', or 'minimal'."""
        fields = [
            context.printer_model,
            context.material,
            context.slicer_settings,
        ]
        filled = sum(1 for f in fields if f)
        if filled >= 3:
            return "full"
        if filled >= 1:
            return "partial"
        return "minimal"

    # ── Defect enrichment (US1) ────────────────────────────────────

    def enrich_defects(self, defects: list[PrintDefect]) -> list[PrintDefect]:
        """Populate severity from knowledge base for each defect."""
        guides = self.load_defect_guides()
        for defect in defects:
            if defect.severity is not None:
                continue
            cat_key = defect.category.value
            guide = guides.get(cat_key, {})
            severity_str = guide.get("severity", "functional")
            try:
                defect.severity = PrintDefectSeverity(severity_str)
            except ValueError:
                defect.severity = PrintDefectSeverity.functional
        return defects

    # ── Decision tree walking (US2) ────────────────────────────────

    def walk_decision_tree(
        self,
        defect: PrintDefect,
        context: DiagnosticContext,
    ) -> list[RootCause]:
        """Walk the decision tree for a defect category using the context."""
        trees = self.load_decision_trees()
        cat_key = defect.category.value
        tree = trees.get(cat_key)
        if tree is None:
            return []

        root_node = tree.get("root", {})
        causes_data = self._walk_node(root_node, context)

        root_causes = []
        for cause in causes_data:
            root_causes.append(
                RootCause(
                    description=cause.get("description", "Unknown cause"),
                    likelihood=cause.get("likelihood", "medium"),
                    contributing_factors=cause.get("contributing_factors", []),
                    defect_category=defect.category,
                )
            )
        return root_causes

    def _walk_node(
        self, node: dict[str, Any], context: DiagnosticContext
    ) -> list[dict[str, Any]]:
        """Recursively walk a decision tree node."""
        # Leaf node — return causes
        if "causes" in node:
            return node["causes"]

        condition = node.get("condition", "")
        branches = node.get("branches", {})
        if not branches:
            return node.get("causes", [])

        # Resolve the condition value from context
        context_value = self._resolve_condition(condition, context)

        # Try exact match first
        if context_value and context_value in branches:
            return self._walk_node(branches[context_value], context)

        # Try case-insensitive match
        if context_value:
            for branch_key, branch_node in branches.items():
                if branch_key == "_default":
                    continue
                if branch_key.lower() == context_value.lower():
                    return self._walk_node(branch_node, context)

        # Fall back to _default
        default = branches.get("_default", {})
        if default:
            return self._walk_node(default, context)

        # No matching branch — collect all leaf causes
        all_causes: list[dict[str, Any]] = []
        for key, branch in branches.items():
            if key != "_default":
                all_causes.extend(self._walk_node(branch, context))
        return all_causes

    def _resolve_condition(
        self, condition: str, context: DiagnosticContext
    ) -> str | None:
        """Map a decision tree condition name to a context field value."""
        mapping: dict[str, str | None] = {
            "material_type": context.material,
            "extruder_type": context.extruder_type,
            "printer_family": context.printer_family,
            "enclosure_type": (
                "enclosed"
                if context.printer_family in ("bambu",)
                else "open" if context.printer_family else None
            ),
        }
        return mapping.get(condition)

    # ── Recommendation generation (US3) ────────────────────────────

    def generate_recommendations(
        self,
        root_causes: list[RootCause],
        context: DiagnosticContext,
        defects: list[PrintDefect],
    ) -> list[Recommendation]:
        """Generate fix recommendations from root causes and context."""
        recommendations: list[Recommendation] = []

        # Build severity lookup for defect categories
        severity_map: dict[PrintDefectCategory, PrintDefectSeverity] = {}
        for d in defects:
            if d.severity:
                severity_map[d.category] = d.severity

        material_data = self.load_material_data()
        printer_data = self.load_printer_data()

        for cause in root_causes:
            cause_recs = self._recs_from_cause(
                cause, context, material_data, printer_data
            )
            recommendations.extend(cause_recs)

        return recommendations

    def _recs_from_cause(
        self,
        cause: RootCause,
        context: DiagnosticContext,
        material_data: dict[str, Any],
        printer_data: dict[str, Any],
    ) -> list[Recommendation]:
        """Extract recommendations from decision tree cause data and knowledge."""
        recs: list[Recommendation] = []

        # The decision tree causes may already have recommendations embedded
        # (populated during tree walking). Check if the cause was built from
        # tree data that included recommendations.
        trees = self.load_decision_trees()
        cat_key = cause.defect_category.value
        tree = trees.get(cat_key, {})

        # Walk the tree again to find the recommendations for this cause
        tree_recs = self._find_recs_for_cause(tree, cause, context)
        for rec_data in tree_recs:
            recs.append(
                Recommendation(
                    setting=rec_data.get("setting", "unknown"),
                    current_issue=rec_data.get("current_issue", ""),
                    suggested_value=rec_data.get("suggested_value", ""),
                    impact=rec_data.get("impact", "medium"),
                    difficulty=rec_data.get("difficulty", "easy"),
                    category=rec_data.get("category", "controllable"),
                    explanation=rec_data.get("explanation", ""),
                )
            )

        # Supplement with material-specific recommendations if available
        if context.material and not recs:
            mat_key = context.material.upper()
            mat = material_data.get(mat_key) or material_data.get(
                context.material.lower()
            )
            if mat:
                mat_recs = mat.get("recommended_settings", {}).get(cat_key, {})
                if isinstance(mat_recs, dict):
                    for setting, value in mat_recs.items():
                        if isinstance(value, dict):
                            recs.append(
                                Recommendation(
                                    setting=setting,
                                    current_issue=value.get(
                                        "current_issue", f"{setting} may need adjustment"
                                    ),
                                    suggested_value=str(value.get("suggested_value", "")),
                                    impact=value.get("impact", "medium"),
                                    difficulty=value.get("difficulty", "easy"),
                                    category=value.get("category", "controllable"),
                                    explanation=value.get(
                                        "explanation",
                                        f"Recommended for {context.material}",
                                    ),
                                )
                            )

        return recs

    def _find_recs_for_cause(
        self,
        tree: dict[str, Any],
        cause: RootCause,
        context: DiagnosticContext,
    ) -> list[dict[str, Any]]:
        """Walk the tree to find recommendations matching a specific cause."""
        root_node = tree.get("root", {})
        causes_data = self._walk_node(root_node, context)
        for c in causes_data:
            if c.get("description") == cause.description:
                return c.get("recommendations", [])
        return []

    # ── Sorting and conflict detection (US3) ───────────────────────

    def sort_recommendations(
        self,
        recommendations: list[Recommendation],
        defects: list[PrintDefect],
        root_causes: list[RootCause],
    ) -> list[Recommendation]:
        """Sort recommendations: severity → impact → difficulty (ease)."""
        # Build a map from recommendation to its defect severity
        cause_severity: dict[str, PrintDefectSeverity] = {}
        defect_severity: dict[PrintDefectCategory, PrintDefectSeverity] = {}
        for d in defects:
            if d.severity:
                defect_severity[d.category] = d.severity
        for rc in root_causes:
            sev = defect_severity.get(rc.defect_category, PrintDefectSeverity.functional)
            cause_severity[rc.description] = sev

        def sort_key(rec: Recommendation) -> tuple[int, int, int]:
            # Find the severity of the defect this recommendation addresses
            # Default to functional if we can't determine
            sev = PrintDefectSeverity.functional
            for rc in root_causes:
                for tree_rec in self._find_recs_for_cause(
                    self.load_decision_trees().get(rc.defect_category.value, {}),
                    rc,
                    DiagnosticContext(),
                ):
                    if tree_rec.get("setting") == rec.setting:
                        sev = cause_severity.get(
                            rc.description, PrintDefectSeverity.functional
                        )
                        break

            return (
                _SEVERITY_ORDER.get(sev, 1),
                _IMPACT_ORDER.get(rec.impact, 1),
                _DIFFICULTY_ORDER.get(rec.difficulty, 1),
            )

        return sorted(recommendations, key=sort_key)

    def detect_conflicts(
        self, recommendations: list[Recommendation]
    ) -> list[str]:
        """Detect conflicting recommendations."""
        conflicts: list[str] = []
        seen: dict[str, list[Recommendation]] = {}

        for rec in recommendations:
            base_setting = rec.setting.lower().replace(" ", "_")
            if base_setting not in seen:
                seen[base_setting] = []
            seen[base_setting].append(rec)

        for setting, recs in seen.items():
            if len(recs) < 2:
                continue
            # Check if recommendations for the same setting suggest
            # different directions
            for pair in _CONFLICT_PAIRS:
                pair_setting, dir1, dir2 = pair
                if pair_setting not in setting:
                    continue
                explanations = [
                    r.explanation.lower() + " " + r.current_issue.lower()
                    for r in recs
                ]
                has_dir1 = any(dir1 in e for e in explanations)
                has_dir2 = any(dir2 in e for e in explanations)
                if has_dir1 and has_dir2:
                    conflicts.append(
                        f"Conflicting recommendations for '{setting}': "
                        f"one suggests to {dir1}, another to {dir2}. "
                        f"Consider a balanced compromise value."
                    )

        # Also check for same setting with different values
        for setting, recs in seen.items():
            if len(recs) >= 2:
                values = {r.suggested_value for r in recs}
                if len(values) > 1 and setting not in [
                    c.split("'")[1] for c in conflicts if "'" in c
                ]:
                    conflicts.append(
                        f"Multiple recommendations for '{setting}' with "
                        f"different values: {', '.join(values)}. "
                        f"Prioritize the fix for the most severe defect."
                    )

        return conflicts
