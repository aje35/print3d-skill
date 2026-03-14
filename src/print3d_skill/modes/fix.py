"""Fix mode handler — routes through the mesh repair pipeline."""

from __future__ import annotations

from print3d_skill.modes.base import ModeHandler
from print3d_skill.models.mode import ModeResponse


class FixHandler(ModeHandler):
    mode_name = "fix"

    def handle(self, **context: object) -> ModeResponse:
        """Handle a Fix mode request by running the repair pipeline.

        Expected context kwargs:
            mesh_path (str): Path to the mesh file to repair.
            output_path (str, optional): Path for repaired output.
            config (RepairConfig, optional): Repair configuration.
        """
        mesh_path = context.get("mesh_path")
        if not mesh_path or not isinstance(mesh_path, str):
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message="Fix mode requires 'mesh_path' parameter.",
                data=None,
            )

        output_path = context.get("output_path")
        config = context.get("config")

        try:
            from print3d_skill.repair import repair_mesh

            summary = repair_mesh(
                mesh_path=mesh_path,
                output_path=output_path if isinstance(output_path, str) else None,
                config=config if config is not None else None,  # type: ignore[arg-type]
            )

            return ModeResponse(
                mode=self.mode_name,
                status="success",
                message=f"Fixed {summary.total_defects_fixed}/{summary.total_defects_found} defects.",
                data=summary,  # type: ignore[arg-type]
            )

        except FileNotFoundError as e:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=str(e),
                data=None,
            )
        except Exception as e:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=f"Fix mode failed: {e}",
                data=None,
            )
