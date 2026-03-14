"""Validate mode handler — wraps validate_gcode() for the mode router."""

from __future__ import annotations

from print3d_skill.models.mode import ModeResponse
from print3d_skill.modes.base import ModeHandler


class ValidateHandler(ModeHandler):
    mode_name = "validate"

    def handle(self, **context: object) -> ModeResponse:
        """Validate G-code against material/printer profiles.

        Expected context kwargs:
            gcode_path (str): Required — path to G-code file.
            material (str | None): Optional material name.
            printer (str | None): Optional printer profile name.
        """
        gcode_path = context.get("gcode_path")
        if not gcode_path or not isinstance(gcode_path, str):
            return ModeResponse(
                mode="validate",
                status="error",
                message="gcode_path is required",
                data={},
            )

        material = context.get("material")
        printer = context.get("printer")

        try:
            from print3d_skill.validate import validate_gcode

            result = validate_gcode(
                gcode_path,
                material=material if isinstance(material, str) else None,
                printer=printer if isinstance(printer, str) else None,
            )
            return ModeResponse(
                mode="validate",
                status="success",
                message=result.summary,
                data={"validation_result": result},
            )
        except Exception as exc:
            return ModeResponse(
                mode="validate",
                status="error",
                message=str(exc),
                data={},
            )
