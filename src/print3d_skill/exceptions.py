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


class MeshAnalysisError(Print3DSkillError):
    """Raised when mesh analysis fails (e.g., no valid geometry)."""


class RepairError(Print3DSkillError):
    """Raised when the repair pipeline encounters an unrecoverable error."""


class ExportError(Print3DSkillError):
    """Raised when mesh export fails (e.g., unable to write output file)."""


class DesignError(Print3DSkillError):
    """Raised when the design pipeline encounters an unrecoverable error."""


class PrintabilityError(Print3DSkillError):
    """Raised when printability validation cannot be performed."""


class GcodeParseError(Print3DSkillError):
    """Raised when a G-code file is corrupted, empty, or cannot be parsed."""


class SlicerError(Print3DSkillError):
    """Raised when a slicer CLI returns a non-zero exit code.

    Attributes:
        slicer: The slicer that failed.
        stderr: The slicer's stderr output.
    """

    def __init__(self, slicer: str, stderr: str = "", message: str = "") -> None:
        self.slicer = slicer
        self.stderr = stderr
        msg = message or f"Slicer '{slicer}' failed"
        if stderr:
            msg += f": {stderr[:500]}"
        super().__init__(msg)


class ValidationError(Print3DSkillError):
    """Raised when G-code fails validation with FAIL status.

    Attributes:
        validation_result: The full validation result that caused the failure.
    """

    def __init__(self, message: str, validation_result: object = None) -> None:
        self.validation_result = validation_result
        super().__init__(message)


class PrinterError(Print3DSkillError):
    """Raised when printer communication fails.

    Attributes:
        printer_name: Name of the printer that failed.
    """

    def __init__(self, printer_name: str, message: str = "") -> None:
        self.printer_name = printer_name
        msg = message or f"Printer '{printer_name}' communication failed"
        super().__init__(msg)
