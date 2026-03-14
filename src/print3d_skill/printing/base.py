"""PrinterBackend abstract base class.

Each backend implements connect/status/upload/start_print/disconnect
for a specific printer API protocol (OctoPrint, Moonraker, Bambu).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from print3d_skill.models.validate import PrinterConnectionType, PrinterInfo


class PrinterBackend(ABC):
    """Base class for printer communication backends.

    Subclasses implement the protocol-specific HTTP/MQTT calls.
    All operations are synchronous and use timeouts to avoid
    blocking indefinitely.
    """

    @property
    @abstractmethod
    def connection_type(self) -> PrinterConnectionType:
        """The connection protocol this backend uses."""

    @abstractmethod
    def connect(self) -> bool:
        """Test connectivity to the printer.

        Returns True if the printer is reachable and authenticated.
        Raises PrinterError on unrecoverable connection failures.
        """

    @abstractmethod
    def status(self) -> PrinterInfo:
        """Query current printer state, temperatures, and progress.

        Returns a PrinterInfo dataclass with current values.
        Raises PrinterError if the printer cannot be reached.
        """

    @abstractmethod
    def upload(self, gcode_path: str) -> bool:
        """Upload a G-code file to the printer's storage.

        Args:
            gcode_path: Local filesystem path to the G-code file.

        Returns True if the upload succeeded.
        Raises PrinterError on transfer failure.
        """

    @abstractmethod
    def start_print(self, filename: str) -> bool:
        """Start printing a previously uploaded G-code file.

        Args:
            filename: The filename on the printer (basename, not full path).

        Returns True if the print job was started.
        Raises PrinterError if the printer refuses the command.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the printer.

        Safe to call multiple times. Does not raise.
        """
