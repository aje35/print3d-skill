"""Printer control backends (extended tier).

Public API:
    list_printers() — discover configured printers and query their status.
    submit_print() — validate G-code, upload, and start a print job.
"""

from __future__ import annotations

import logging
from pathlib import Path

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    PrinterError,
    ValidationError,
)
from print3d_skill.models.validate import (
    PrinterConnection,
    PrinterConnectionType,
    PrinterInfo,
    PrinterStatus,
    PrintJob,
    ValidationStatus,
)
from print3d_skill.printing.base import PrinterBackend

logger = logging.getLogger(__name__)


def list_printers() -> list[PrinterInfo]:
    """Load printer config and query each printer's status.

    Returns a list of PrinterInfo for all configured printers.
    Printers that fail to connect get DISCONNECTED status rather
    than raising an exception.

    Raises:
        CapabilityUnavailable: No printer config file found.
    """
    from print3d_skill.printing.config import load_printer_config

    connections = load_printer_config()
    if not connections:
        raise CapabilityUnavailable(
            capability="printer_control",
            provider="printer config",
            install_instructions=(
                "Create a printer config file. "
                "See docs for format: ~/.config/print3d-skill/printers.yaml"
            ),
        )

    results: list[PrinterInfo] = []
    for conn in connections:
        try:
            backend = _create_backend(conn)
            backend.connect()
            info = backend.status()
            results.append(info)
            backend.disconnect()
        except (PrinterError, CapabilityUnavailable) as exc:
            logger.warning("Printer '%s' unavailable: %s", conn.name, exc)
            results.append(
                PrinterInfo(
                    name=conn.name,
                    connection_type=conn.connection_type,
                    status=PrinterStatus.DISCONNECTED,
                )
            )

    return results


def submit_print(
    gcode_path: str,
    printer_name: str,
    material: str | None = None,
    printer_profile: str | None = None,
) -> PrintJob:
    """Validate G-code, upload to a printer, and start the print.

    ALWAYS validates the G-code before submitting. If validation
    returns FAIL status, raises ValidationError without sending
    to the printer.

    Args:
        gcode_path: Path to the G-code file.
        printer_name: Name of the printer (must match config).
        material: Material name for validation (e.g., "PLA").
        printer_profile: Printer profile name for validation.

    Returns:
        PrintJob with submission details and validation result.

    Raises:
        ValidationError: G-code validation failed.
        PrinterError: Printer is in ERROR state or communication failed.
        CapabilityUnavailable: No printer config or printer not found.
        FileNotFoundError: G-code file does not exist.
    """
    # Validate the G-code file exists
    path = Path(gcode_path)
    if not path.exists():
        raise FileNotFoundError(f"G-code file not found: {gcode_path}")

    # ALWAYS validate first
    from print3d_skill.validate import validate_gcode

    validation_result = validate_gcode(
        gcode_path=gcode_path,
        material=material,
        printer=printer_profile,
    )

    if validation_result.status == ValidationStatus.FAIL:
        raise ValidationError(
            f"G-code validation failed: {'; '.join(validation_result.failures)}",
            validation_result=validation_result,
        )

    # Find the printer
    from print3d_skill.printing.config import load_printer_config

    connections = load_printer_config()
    if not connections:
        raise CapabilityUnavailable(
            capability="printer_control",
            provider="printer config",
            install_instructions="Create a printer config file",
        )

    conn = _find_printer(connections, printer_name)

    # Connect and check state
    backend = _create_backend(conn)
    backend.connect()

    try:
        info = backend.status()
        if info.status == PrinterStatus.ERROR:
            raise PrinterError(
                printer_name,
                f"Printer '{printer_name}' is in ERROR state — "
                "clear the error before submitting a print",
            )

        # Upload and start
        filename = path.name
        backend.upload(gcode_path)
        backend.start_print(filename)

        return PrintJob(
            printer_name=printer_name,
            gcode_path=gcode_path,
            validation_result=validation_result,
            submitted=True,
            message=f"Print job submitted to '{printer_name}': {filename}",
        )
    finally:
        backend.disconnect()


def _create_backend(connection: PrinterConnection) -> PrinterBackend:
    """Create the appropriate backend for a printer connection type."""
    if connection.connection_type == PrinterConnectionType.OCTOPRINT:
        from print3d_skill.printing.octoprint import OctoPrintBackend

        return OctoPrintBackend(connection)
    elif connection.connection_type == PrinterConnectionType.MOONRAKER:
        from print3d_skill.printing.moonraker import MoonrakerBackend

        return MoonrakerBackend(connection)
    elif connection.connection_type == PrinterConnectionType.BAMBU:
        from print3d_skill.printing.bambu import BambuBackend

        return BambuBackend(connection)
    else:
        raise PrinterError(
            connection.name,
            f"Unknown connection type: {connection.connection_type}",
        )


def _find_printer(connections: list[PrinterConnection], printer_name: str) -> PrinterConnection:
    """Find a printer connection by name."""
    for conn in connections:
        if conn.name == printer_name:
            return conn
    available = ", ".join(c.name for c in connections)
    raise PrinterError(
        printer_name,
        f"Printer '{printer_name}' not found in config. Available: {available}",
    )
