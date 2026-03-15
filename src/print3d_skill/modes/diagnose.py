"""Diagnose mode handler.

Accepts pre-identified defect categories and diagnostic context,
runs the diagnosis pipeline, and returns a ModeResponse with
root causes, recommendations, and conflict warnings.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from print3d_skill.diagnosis import diagnose_print
from print3d_skill.diagnosis.models import (
    DiagnosticContext,
    PrintDefect,
    PrintDefectCategory,
)
from print3d_skill.models.mode import ModeResponse
from print3d_skill.modes.base import ModeHandler


class DiagnoseHandler(ModeHandler):
    mode_name = "diagnose"

    def handle(self, **context: object) -> ModeResponse:
        """Handle a diagnosis request.

        Expected context keys:
            defects: list[dict] — Each dict has category, description, confidence
            printer: str — Printer model name (optional)
            material: str — Material type (optional)
            slicer_settings: dict — Key slicer settings (optional)
            geometry_info: dict — Model characteristics (optional)
        """
        raw_defects = context.get("defects")
        if not raw_defects or not isinstance(raw_defects, list):
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message="No defects provided. Pass a 'defects' list of dicts "
                "with 'category', 'description', and 'confidence' keys.",
            )

        try:
            defects = self._parse_defects(raw_defects)
        except (KeyError, ValueError) as exc:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=f"Invalid defect data: {exc}",
            )

        diag_context = DiagnosticContext(
            printer_model=_str_or_none(context.get("printer")),
            material=_str_or_none(context.get("material")),
            slicer_settings=_dict_or_none(context.get("slicer_settings")),
            geometry_info=_dict_or_none(context.get("geometry_info")),
        )

        try:
            result = diagnose_print(defects, diag_context)
        except Exception as exc:  # noqa: BLE001
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=f"Diagnosis failed: {exc}",
            )

        # Serialize result to dict for ModeResponse.data
        result_data = asdict(result)
        # Convert enum values to strings for JSON serialization
        _stringify_enums(result_data)

        cause_count = len(result.root_causes)
        rec_count = len(result.recommendations)
        defect_count = len(result.defects)
        conflict_count = len(result.conflicts)

        summary_parts = [
            f"Diagnosed {defect_count} defect(s)",
            f"found {cause_count} root cause(s)",
            f"generated {rec_count} recommendation(s)",
        ]
        if conflict_count:
            summary_parts.append(f"detected {conflict_count} conflict(s)")
        summary_parts.append(f"context quality: {result.context_quality}")

        return ModeResponse(
            mode=self.mode_name,
            status="success",
            message=", ".join(summary_parts),
            data=result_data,
        )

    @staticmethod
    def _parse_defects(raw_defects: list[Any]) -> list[PrintDefect]:
        """Convert raw dict defects to PrintDefect objects."""
        defects = []
        for raw in raw_defects:
            if isinstance(raw, PrintDefect):
                defects.append(raw)
                continue
            if not isinstance(raw, dict):
                raise ValueError(f"Expected dict, got {type(raw).__name__}")
            category = PrintDefectCategory(raw["category"])
            defects.append(
                PrintDefect(
                    category=category,
                    description=raw.get("description", ""),
                    confidence=raw.get("confidence", "medium"),
                    spatial_distribution=raw.get("spatial_distribution", "global"),
                )
            )
        return defects


def _str_or_none(val: object) -> str | None:
    return str(val) if val is not None else None


def _dict_or_none(val: object) -> dict[str, Any] | None:
    return val if isinstance(val, dict) else None


def _stringify_enums(data: Any) -> None:
    """Recursively convert enum values to strings in a dict/list structure."""
    if isinstance(data, dict):
        for key, val in data.items():
            if hasattr(val, "value"):
                data[key] = val.value
            elif isinstance(val, (dict, list)):
                _stringify_enums(val)
    elif isinstance(data, list):
        for i, val in enumerate(data):
            if hasattr(val, "value"):
                data[i] = val.value
            elif isinstance(val, (dict, list)):
                _stringify_enums(val)
