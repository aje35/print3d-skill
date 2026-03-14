"""Slicer CLI integration (extended tier).

Public API: slice_model()
"""

from __future__ import annotations

from pathlib import Path

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    UnsupportedFormatError,
)
from print3d_skill.exceptions import (
    SlicerError as SlicerError,
)
from print3d_skill.models.validate import SliceResult, SlicerType
from print3d_skill.slicing.orcaslicer import OrcaSlicerBackend
from print3d_skill.slicing.prusaslicer import PrusaSlicerBackend

_SUPPORTED_EXTENSIONS = {".stl", ".3mf"}


def slice_model(
    model_path: str | Path,
    output_path: str | Path | None = None,
    slicer: SlicerType | None = None,
    printer_profile: str | None = None,
    material_profile: str | None = None,
    quality_preset: str | None = None,
    **overrides: str,
) -> SliceResult:
    """Slice a 3D model to G-code using an available slicer CLI.

    Args:
        model_path: Path to the input .stl or .3mf file.
        output_path: Path for the output .gcode file. If None, generates
            ``<model_stem>_sliced.gcode`` alongside the input.
        slicer: Force a specific slicer backend. If None, auto-detects
            (tries PrusaSlicer first, then OrcaSlicer).
        printer_profile: Path to a printer profile/config file.
        material_profile: Path to a material/filament profile file.
        quality_preset: Path to a print quality preset file.
        **overrides: Slicer setting overrides as key=value pairs.

    Returns:
        SliceResult with gcode path, slicer info, and applied settings.

    Raises:
        FileNotFoundError: If model_path does not exist.
        UnsupportedFormatError: If model_path has an unsupported extension.
        CapabilityUnavailable: If no slicer CLI is detected.
        SlicerError: If the slicer CLI returns a non-zero exit code.
    """
    model = Path(model_path)

    # Validate model file exists
    if not model.is_file():
        raise FileNotFoundError(f"Model file not found: {model}")

    # Validate extension
    ext = model.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        raise UnsupportedFormatError(f"Unsupported format '{ext}'. Supported: {supported}")

    # Resolve output path
    if output_path is None:
        out = model.parent / f"{model.stem}_sliced.gcode"
    else:
        out = Path(output_path)

    # Select backend
    backend = _resolve_backend(slicer)

    return backend.slice(
        model_path=model,
        output_path=out,
        printer_profile=printer_profile,
        material_profile=material_profile,
        quality_preset=quality_preset,
        overrides=overrides if overrides else None,
    )


def _resolve_backend(slicer: SlicerType | None):
    """Pick a slicer backend, auto-detecting if not specified."""
    backends = {
        SlicerType.PRUSASLICER: PrusaSlicerBackend,
        SlicerType.ORCASLICER: OrcaSlicerBackend,
    }

    if slicer is not None:
        backend = backends[slicer]()
        if not backend.detect():
            raise CapabilityUnavailable(
                capability="gcode_slicing",
                provider=slicer.value,
                install_instructions=_install_instructions(slicer),
            )
        return backend

    # Auto-detect: try PrusaSlicer first, then OrcaSlicer
    for slicer_type in (SlicerType.PRUSASLICER, SlicerType.ORCASLICER):
        backend = backends[slicer_type]()
        if backend.detect():
            return backend

    raise CapabilityUnavailable(
        capability="gcode_slicing",
        provider="slicer",
        install_instructions=(
            "Install PrusaSlicer (https://github.com/prusa3d/PrusaSlicer) "
            "or OrcaSlicer (https://github.com/SoftFever/OrcaSlicer)"
        ),
    )


def _install_instructions(slicer_type: SlicerType) -> str:
    """Return install instructions for a specific slicer."""
    if slicer_type == SlicerType.PRUSASLICER:
        return (
            "Install PrusaSlicer: https://github.com/prusa3d/PrusaSlicer/releases "
            "and ensure prusa-slicer is on PATH"
        )
    return (
        "Install OrcaSlicer: https://github.com/SoftFever/OrcaSlicer/releases "
        "and ensure orca-slicer is on PATH"
    )
