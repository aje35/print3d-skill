"""PrusaSlicer CLI backend."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from print3d_skill.exceptions import SlicerError
from print3d_skill.models.validate import SliceResult, SlicerType
from print3d_skill.slicing.base import SlicerBackend

_TIMEOUT_S = 120


class PrusaSlicerBackend(SlicerBackend):
    """PrusaSlicer CLI integration.

    Detects ``prusa-slicer`` or ``PrusaSlicer`` on PATH and drives
    slicing via ``--export-gcode``.
    """

    @property
    def slicer_type(self) -> SlicerType:
        return SlicerType.PRUSASLICER

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _find_executable(self) -> str | None:
        """Return the executable name if found on PATH."""
        for name in ("prusa-slicer", "PrusaSlicer"):
            if shutil.which(name) is not None:
                return name
        return None

    def detect(self) -> bool:
        return self._find_executable() is not None

    def get_version(self) -> str | None:
        exe = self._find_executable()
        if exe is None:
            return None

        try:
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # PrusaSlicer prints version to stdout or stderr depending on build
            version_text = result.stdout.strip() or result.stderr.strip()
            if version_text:
                # e.g. "PrusaSlicer-2.7.1+linux-x64-..."  or just "2.7.1"
                parts = version_text.split()
                return parts[0] if parts else version_text
        except (subprocess.TimeoutExpired, OSError):
            pass

        return None

    # ------------------------------------------------------------------
    # Slicing
    # ------------------------------------------------------------------

    def slice(
        self,
        model_path: Path,
        output_path: Path,
        printer_profile: str | None = None,
        material_profile: str | None = None,
        quality_preset: str | None = None,
        overrides: dict[str, str] | None = None,
    ) -> SliceResult:
        exe = self._find_executable()
        if exe is None:
            raise SlicerError("prusaslicer", message="PrusaSlicer not found on PATH")

        cmd: list[str] = [exe, "--export-gcode"]

        # Profile loading
        profiles_used: dict[str, str] = {}
        if printer_profile:
            cmd.extend(["--load", printer_profile])
            profiles_used["printer"] = printer_profile
        if material_profile:
            cmd.extend(["--load", material_profile])
            profiles_used["material"] = material_profile
        if quality_preset:
            cmd.extend(["--load", quality_preset])
            profiles_used["quality"] = quality_preset

        # Override settings via a temporary INI file
        overrides_applied: dict[str, str] = {}
        tmp_ini_path: str | None = None
        if overrides:
            tmp_ini = tempfile.NamedTemporaryFile(
                mode="w", suffix=".ini", delete=False, prefix="print3d_overrides_"
            )
            try:
                for key, value in overrides.items():
                    tmp_ini.write(f"{key} = {value}\n")
                tmp_ini.flush()
                tmp_ini_path = tmp_ini.name
                cmd.extend(["--load", tmp_ini_path])
                overrides_applied = dict(overrides)
            finally:
                tmp_ini.close()

        cmd.extend(["-o", str(output_path), str(model_path)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as exc:
            raise SlicerError(
                "prusaslicer",
                message=f"PrusaSlicer timed out after {_TIMEOUT_S}s",
            ) from exc
        finally:
            # Clean up temp INI
            if tmp_ini_path:
                Path(tmp_ini_path).unlink(missing_ok=True)

        if result.returncode != 0:
            raise SlicerError("prusaslicer", stderr=result.stderr)

        # Collect warnings from stderr (non-fatal output)
        warnings: list[str] = []
        if result.stderr.strip():
            warnings.append(result.stderr.strip())

        version = self.get_version() or ""

        return SliceResult(
            gcode_path=str(output_path),
            slicer_used=SlicerType.PRUSASLICER,
            slicer_version=version,
            model_path=str(model_path),
            profiles_used=profiles_used,
            overrides_applied=overrides_applied,
            warnings=warnings,
        )
