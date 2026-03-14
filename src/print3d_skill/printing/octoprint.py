"""OctoPrint printer backend.

Communicates with OctoPrint's REST API using the requests library.
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


class OctoPrintBackend(PrinterBackend):
    """OctoPrint REST API backend.

    Uses GET/POST requests with X-Api-Key authentication.
    The requests library is lazily imported and degrades
    gracefully if not installed.
    """

    def __init__(self, connection: PrinterConnection) -> None:
        self._connection = connection
        port = connection.port or 5000
        self._base_url = f"http://{connection.host}:{port}/api"
        self._headers = {"X-Api-Key": connection.api_key or ""}

    @property
    def connection_type(self) -> PrinterConnectionType:
        return PrinterConnectionType.OCTOPRINT

    def connect(self) -> bool:
        """Test connectivity via GET /api/version."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.get(
                f"{self._base_url}/version",
                headers=self._headers,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("OctoPrint connected: %s", resp.json())
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach OctoPrint at {self._connection.host}: {exc}",
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise PrinterError(
                self._connection.name,
                f"OctoPrint auth failed (check API key): {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"OctoPrint connection timed out: {exc}",
            ) from exc

    def status(self) -> PrinterInfo:
        """Query printer state via GET /api/printer."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.get(
                f"{self._base_url}/printer",
                headers=self._headers,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            state_text = data.get("state", {}).get("text", "").lower()
            printer_status = _parse_octoprint_state(state_text)

            temps = data.get("temperature", {})
            hotend = temps.get("tool0", {}).get("actual")
            bed = temps.get("bed", {}).get("actual")

            return PrinterInfo(
                name=self._connection.name,
                connection_type=PrinterConnectionType.OCTOPRINT,
                status=printer_status,
                hotend_temp_c=hotend,
                bed_temp_c=bed,
            )
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach OctoPrint: {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"OctoPrint status request timed out: {exc}",
            ) from exc

    def upload(self, gcode_path: str) -> bool:
        """Upload G-code via POST /api/files/local (multipart)."""
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
                    f"{self._base_url}/files/local",
                    headers=self._headers,
                    files={"file": (path.name, fh, "application/octet-stream")},
                    timeout=120,  # uploads can be large
                )
            resp.raise_for_status()
            logger.debug("Uploaded %s to OctoPrint", path.name)
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Upload failed — cannot reach OctoPrint: {exc}",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise PrinterError(
                self._connection.name,
                f"Upload timed out: {exc}",
            ) from exc

    def start_print(self, filename: str) -> bool:
        """Start printing via POST /api/files/local/<filename>."""
        requests = _import_requests(self._connection.name)
        try:
            resp = requests.post(
                f"{self._base_url}/files/local/{filename}",
                headers=self._headers,
                json={"command": "select", "print": True},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("Started print: %s", filename)
            return True
        except requests.exceptions.ConnectionError as exc:
            raise PrinterError(
                self._connection.name,
                f"Cannot reach OctoPrint to start print: {exc}",
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise PrinterError(
                self._connection.name,
                f"Failed to start print '{filename}': {exc}",
            ) from exc

    def disconnect(self) -> None:
        """No persistent connection to close for REST API."""
        logger.debug("OctoPrint disconnect (no-op for REST)")


def _import_requests(printer_name: str):
    """Lazily import requests, raising a clear error if missing."""
    try:
        import requests

        return requests
    except ImportError as exc:
        raise PrinterError(
            printer_name,
            "The 'requests' package is required for OctoPrint. Install with: pip install requests",
        ) from exc


def _parse_octoprint_state(state_text: str) -> PrinterStatus:
    """Map OctoPrint state string to PrinterStatus enum."""
    if "printing" in state_text:
        return PrinterStatus.PRINTING
    if "paused" in state_text or "pausing" in state_text:
        return PrinterStatus.PAUSED
    if "error" in state_text:
        return PrinterStatus.ERROR
    if "operational" in state_text or "ready" in state_text:
        return PrinterStatus.IDLE
    if "offline" in state_text or "closed" in state_text:
        return PrinterStatus.DISCONNECTED
    return PrinterStatus.UNKNOWN
