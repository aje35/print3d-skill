"""ModeHandler base class with default stub response."""

from __future__ import annotations

from abc import ABC

from print3d_skill.models.mode import ModeResponse


class ModeHandler(ABC):
    """Base class for workflow mode handlers.

    Subclasses implement handle() to process requests for their mode.
    The default implementation returns a not_implemented response.
    """

    mode_name: str = ""

    def handle(self, **context: object) -> ModeResponse:
        """Handle a request for this mode.

        Override in subclasses for actual implementations.
        Default returns not_implemented status.
        """
        return ModeResponse(
            mode=self.mode_name,
            status="not_implemented",
            message=f"The '{self.mode_name}' mode is not yet implemented.",
            data=None,
        )
