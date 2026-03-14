"""Skill router: dispatches user intent to the appropriate mode handler."""

from __future__ import annotations

from print3d_skill.exceptions import InvalidModeError
from print3d_skill.models.mode import ModeResponse, WorkflowMode
from print3d_skill.modes.base import ModeHandler
from print3d_skill.modes.create import CreateHandler
from print3d_skill.modes.diagnose import DiagnoseHandler
from print3d_skill.modes.fix import FixHandler
from print3d_skill.modes.modify import ModifyHandler
from print3d_skill.modes.validate import ValidateHandler

_HANDLERS: dict[str, ModeHandler] = {
    WorkflowMode.CREATE.value: CreateHandler(),
    WorkflowMode.FIX.value: FixHandler(),
    WorkflowMode.MODIFY.value: ModifyHandler(),
    WorkflowMode.DIAGNOSE.value: DiagnoseHandler(),
    WorkflowMode.VALIDATE.value: ValidateHandler(),
}


def route(mode: str, **context: object) -> ModeResponse:
    """Dispatch to the appropriate workflow handler.

    Valid modes: "create", "fix", "modify", "diagnose", "validate"

    Returns ModeResponse with status and result data.
    For unimplemented handlers, status is "not_implemented".

    Raises:
        InvalidModeError: mode string not recognized.
            Exception message lists valid modes.
    """
    handler = _HANDLERS.get(mode)
    if handler is None:
        raise InvalidModeError(mode)
    return handler.handle(**context)
