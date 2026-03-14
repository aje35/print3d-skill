"""Exception hierarchy for print3d-skill.

All public exceptions inherit from Print3DSkillError so callers
can catch the base class for broad error handling.
"""

from __future__ import annotations


class Print3DSkillError(Exception):
    """Base exception for all print3d-skill errors."""


class MeshLoadError(Print3DSkillError):
    """Raised when a mesh file is corrupt or unreadable."""


class UnsupportedFormatError(Print3DSkillError):
    """Raised when a file format is not recognized."""


class RenderTimeoutError(Print3DSkillError):
    """Raised when rendering exceeds the configured timeout."""


class ScadCompileError(Print3DSkillError):
    """Raised when an OpenSCAD .scad file has syntax or compile errors.

    The exception message includes the compiler output.
    """


class CapabilityUnavailable(Print3DSkillError):
    """Raised when a requested capability is not installed.

    Attributes:
        capability: The capability name that was requested.
        provider: The tool that would provide it.
        install_instructions: How to install the missing tool.
    """

    def __init__(
        self,
        capability: str,
        provider: str = "",
        install_instructions: str = "",
    ) -> None:
        self.capability = capability
        self.provider = provider
        self.install_instructions = install_instructions
        msg = f"Capability '{capability}' is not available"
        if provider:
            msg += f" (provided by {provider})"
        if install_instructions:
            msg += f". Install: {install_instructions}"
        super().__init__(msg)


class InvalidModeError(Print3DSkillError):
    """Raised when an unrecognized mode identifier is given.

    The exception message lists valid modes.
    """

    VALID_MODES = ("create", "fix", "modify", "diagnose", "validate")

    def __init__(self, mode: str) -> None:
        self.mode = mode
        valid = ", ".join(self.VALID_MODES)
        super().__init__(
            f"Unknown mode '{mode}'. Valid modes: {valid}"
        )


class KnowledgeSchemaError(Print3DSkillError):
    """Raised when a knowledge file fails schema validation."""
