"""Printer configuration loader.

Reads printer connection details from a YAML config file at
a platform-appropriate path. Credentials (api_key, access_code)
are NEVER logged.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from print3d_skill.models.validate import PrinterConnection, PrinterConnectionType

logger = logging.getLogger(__name__)


def _config_path() -> Path:
    """Return the platform-appropriate config file path."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / other — follow XDG convention
        base = Path.home() / ".config"
    return base / "print3d-skill" / "printers.yaml"


def load_printer_config() -> list[PrinterConnection]:
    """Load printer connections from the YAML config file.

    Returns an empty list if the config file does not exist.
    Credentials are never logged.

    Returns:
        List of PrinterConnection dataclasses parsed from the config.
    """
    path = _config_path()
    if not path.exists():
        logger.debug("No printer config found at %s", path)
        return []

    import yaml

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not data or "printers" not in data:
        logger.warning("Printer config at %s has no 'printers' key", path)
        return []

    printers: list[PrinterConnection] = []
    for entry in data["printers"]:
        try:
            conn_type = PrinterConnectionType(entry.get("type", "octoprint"))
            conn = PrinterConnection(
                name=entry.get("name", ""),
                connection_type=conn_type,
                host=entry.get("host", ""),
                port=entry.get("port"),
                api_key=entry.get("api_key"),
                serial=entry.get("serial"),
                access_code=entry.get("access_code"),
            )
            printers.append(conn)
            # Log name and host only — NEVER log credentials
            logger.debug("Loaded printer config: %s at %s", conn.name, conn.host)
        except (ValueError, KeyError) as exc:
            logger.warning("Skipping invalid printer entry: %s", exc)

    return printers
