"""Abstract base class for slicer CLI backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from print3d_skill.models.validate import SliceResult, SlicerType


class SlicerBackend(ABC):
    """Base class for slicer CLI integrations.

    Each backend wraps a specific slicer executable (PrusaSlicer,
    OrcaSlicer, etc.) and provides a uniform slicing interface.
    """

    @property
    @abstractmethod
    def slicer_type(self) -> SlicerType:
        """Return the slicer type enum for this backend."""

    @abstractmethod
    def detect(self) -> bool:
        """Check if the slicer CLI is available on this system.

        Returns True if the executable is found and usable.
        """

    @abstractmethod
    def get_version(self) -> str | None:
        """Return the detected version string, or None if unavailable."""

    @abstractmethod
    def slice(
        self,
        model_path: Path,
        output_path: Path,
        printer_profile: str | None = None,
        material_profile: str | None = None,
        quality_preset: str | None = None,
        overrides: dict[str, str] | None = None,
    ) -> SliceResult:
        """Slice a model file to G-code.

        Args:
            model_path: Path to the input .stl or .3mf file.
            output_path: Path for the output .gcode file.
            printer_profile: Path to a printer profile/config file.
            material_profile: Path to a material/filament profile file.
            quality_preset: Path to a print quality preset file.
            overrides: Key-value pairs for slicer setting overrides.

        Returns:
            SliceResult with paths and metadata.

        Raises:
            SlicerError: If the slicer CLI returns a non-zero exit code.
        """
