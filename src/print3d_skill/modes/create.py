"""Create mode handler for parametric CAD generation."""

from __future__ import annotations

from print3d_skill.create import create_design
from print3d_skill.models.create import CreateConfig, DesignRequest
from print3d_skill.models.mode import ModeResponse
from print3d_skill.modes.base import ModeHandler


class CreateHandler(ModeHandler):
    mode_name = "create"

    def handle(self, **context: object) -> ModeResponse:
        """Handle a Create mode request.

        Accepted kwargs:
            description (str): Natural language description of the part.
            dimensions (dict, optional): Explicit dimensions.
            material (str, optional): Target material.
            config (CreateConfig, optional): Pipeline configuration.
        """
        description = context.get("description")
        if not description or not isinstance(description, str):
            return ModeResponse(
                mode=self.mode_name,
                status="error",
                message=(
                    "Create mode requires a 'description' parameter "
                    "with a natural language description of the part."
                ),
            )

        dimensions = context.get("dimensions")
        if dimensions is not None and not isinstance(dimensions, dict):
            dimensions = {}

        material = context.get("material")
        if material is not None and not isinstance(material, str):
            material = None

        request = DesignRequest(
            description=str(description),
            dimensions=dimensions or {},
            material=material if isinstance(material, str) else None,
        )

        config = context.get("config")
        if not isinstance(config, CreateConfig):
            config = None

        result = create_design(request, config)

        return ModeResponse(
            mode=self.mode_name,
            status=result.status,
            message=result.message,
            data={"create_result": result},
        )
