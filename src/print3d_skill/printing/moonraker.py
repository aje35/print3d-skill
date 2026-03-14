"""Moonraker/Klipper printer backend.

Communicates with Moonraker's REST API using the requests library.
Requires the requests package (pip install requests).
"""

from __future__ import annotations

import logging
from pathlib import Path

from print3d_skill.exceptions import PrinterError
from print3d_skill.models.validate import (
    PrinterConnection,
    PrinterConnectionType,
    PrinterInfo,
    PrinterStatus,
)
from print3d_skill.printing.base import PrinterBackend

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds for all HTTP requests


class MoonrakerBackend(PrinterBackend):
    """Moonraker REST API backend for Klipper-based printers.

    Uses GET/POST requests. Authentication is typically IP-based
    (trusted clients) or via API key header.
    """

    def __init__(self, connection: PrinterConnection) -> None:
        self._connection = connection
        port = connection.port or 7125
        self._base_url = f"http://{connection.host}:{port}"
        self._headers: dict[str, str] = {}
        if connection.api_key:
            self._headers["X-Api-Key"] = connection.api_key

    @property
    def connection_type(self) -> PrinterConnectionType:
        return PrinterConnectionType.MOONRAKER

    def connect(self) -> bool:
        """Test connectivity via GET /printer/info."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.get(
                f"{self._base_url}/printer/info",
                headers=self._headers,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("Moonraker connected: %s", resp.json())
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach Moonraker at {self._connection.host}: {exc}",
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise PrinterError(
                self._connection.name,
                f"Moonraker auth failed: {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"Moonraker connection timed out: {exc}",
            ) from exc

    def status(self) -> PrinterInfo:
        """Query printer state via GET /printer/objects/query."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.get(
                f"{self._base_url}/printer/objects/query",
                headers=self._headers,
                params={"print_stats": "", "heater_bed": "", "extruder": ""},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", {}).get("status", {})
            print_stats = result.get("print_stats", {})
            extruder = result.get("extruder", {})
            heater_bed = result.get("heater_bed", {})

            state_text = print_stats.get("state", "").lower()
            printer_status = _parse_moonraker_state(state_text)

            # Calculate progress from print_stats if available
            progress = None
            total_duration = print_stats.get("total_duration", 0)
            print_duration = print_stats.get("print_duration", 0)
            if total_duration > 0 and print_duration > 0:
                # Approximate progress — Moonraker provides this via display_status
                pass

            return PrinterInfo(
                name=self._connection.name,
                connection_type=PrinterConnectionType.MOONRAKER,
                status=printer_status,
                hotend_temp_c=extruder.get("temperature"),
                bed_temp_c=heater_bed.get("temperature"),
                progress_percent=progress,
                current_file=print_stats.get("filename") or None,
            )
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach Moonraker: {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"Moonraker status request timed out: {exc}",
            ) from exc

    def upload(self, gcode_path: str) -> bool:
        """Upload G-code via POST /server/files/upload (multipart)."""
        requests = _import_requests(self._connection.name)
        path = Path(gcode_path)
        if not path.exists():
            raise PrinterError(
                self._connection.name,
                f"G-code file not found: {gcode_path}",
            )
        try:
            with open(path, "rb") as fh:
                resp = requests.post(
                    f"{self._base_url}/server/files/upload",
                    headers=self._headers,
                    files={"file": (path.name, fh, "application/octet-stream")},
                    timeout=120,  # uploads can be large
                )
            resp.raise_for_status()
            logger.debug("Uploaded %s to Moonraker", path.name)
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Upload failed — cannot reach Moonraker: {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"Upload timed out: {exc}",
            ) from exc

    def start_print(self, filename: str) -> bool:
        """Start printing via POST /printer/print/start."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.post(
                f"{self._base_url}/printer/print/start",
                headers=self._headers,
                params={"filename": filename},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("Started print: %s", filename)
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach Moonraker to start print: {exc}",
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise PrinterError(
                self._connection.name,
                f"Failed to start print '{filename}': {exc}",
            ) from exc

    def disconnect(self) -> None:
        """No persistent connection to close for REST API."""
        logger.debug("Moonraker disconnect (no-op for REST)")


def _import_requests(printer_name: str):
    """Lazily import requests, raising a clear error if missing."""
    try:
        import requests

        return requests
    except ImportError as exc:
        raise PrinterError(
            printer_name,
            "The 'requests' package is required for Moonraker. Install with: pip install requests",
        ) from exc


def _parse_moonraker_state(state_text: str) -> PrinterStatus:
    """Map Klipper/Moonraker state string to PrinterStatus enum."""
    if state_text == "printing":
        return PrinterStatus.PRINTING
    if state_text == "paused":
        return PrinterStatus.PAUSED
    if state_text == "error":
        return PrinterStatus.ERROR
    if state_text in ("standby", "ready", "complete"):
        return PrinterStatus.IDLE
    if state_text in ("shutdown", "startup", "disconnected"):
        return PrinterStatus.DISCONNECTED
    return PrinterStatus.UNKNOWN
