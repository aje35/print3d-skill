"""Modify mode handler: dispatches mesh modification operations."""

from __future__ import annotations

from print3d_skill.models.mode import ModeResponse
from print3d_skill.modes.base import ModeHandler


class ModifyHandler(ModeHandler):
    mode_name = "modify"

    def handle(self, **context: object) -> ModeResponse:
        """Handle a Modify mode request.

        Accepted kwargs:
            mesh_path (str): Path to the input mesh file.
            operation (str): Operation type.
            output_path (str, optional): Output file path.
            **params: Operation-specific parameters.
        """
        mesh_path = context.get("mesh_path")
        if not mesh_path or not isinstance(mesh_path, str):
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=(
                    "Modify mode requires a 'mesh_path' parameter "
                    "with the path to the input mesh file."
                ),
            )

        operation = context.get("operation")
        if not operation or not isinstance(operation, str):
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=(
                    "Modify mode requires an 'operation' parameter. "
                    "Valid: boolean, scale, combine, engrave, split"
                ),
            )

        output_path = context.get("output_path")
        if output_path is not None and not isinstance(output_path, str):
            output_path = None

        # Filter out the known keys and pass the rest as params
        known_keys = {"mesh_path", "operation", "output_path"}
        params = {k: v for k, v in context.items() if k not in known_keys}

        try:
            from print3d_skill.modify import modify_mesh

            result = modify_mesh(
                mesh_path=str(mesh_path),
                operation=str(operation),
                output_path=output_path,
                **params,
            )
            return ModeResponse(
                mode=self.mode_name,
                status="success",
                message=f"Modification '{operation}' completed successfully.",
                data={"modify_result": result},
            )
        except FileNotFoundError as e:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=str(e),
            )
        except ValueError as e:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=str(e),
            )
        except Exception as e:
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=f"Modification failed: {e}",
            )
