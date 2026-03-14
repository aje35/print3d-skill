"""Unit tests for printer backends (T032).

Tests cover:
- OctoPrintBackend: connect, status, upload, and start_print via mocked requests
- MoonrakerBackend: connect, status, upload, and start_print via mocked requests
- BambuBackend: connect and status via mocked paho-mqtt client
- Config loading from a temp printers.yaml file
- list_printers() raises CapabilityUnavailable when config has no entries
- _find_printer() raises PrinterError for an unknown printer name
- submit_print() raises ValidationError when validate_gcode returns FAIL status

All HTTP and MQTT calls are mocked — no real printers or network is required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    PrinterError,
    ValidationError,
)
from print3d_skill.models.validate import (
    PrinterConnection,
    PrinterConnectionType,
    PrinterStatus,
    ValidationResult,
    ValidationStatus,
)
from print3d_skill.printing.bambu import BambuBackend, _parse_bambu_report
from print3d_skill.printing.moonraker import MoonrakerBackend, _parse_moonraker_state
from print3d_skill.printing.octoprint import OctoPrintBackend

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _octoprint_conn(
    host: str = "192.168.1.10",
    port: int = 5000,
    api_key: str = "test-api-key",
) -> PrinterConnection:
    return PrinterConnection(
        name="test-octoprint",
        connection_type=PrinterConnectionType.OCTOPRINT,
        host=host,
        port=port,
        api_key=api_key,
    )


def _moonraker_conn(
    host: str = "192.168.1.20",
    port: int = 7125,
) -> PrinterConnection:
    return PrinterConnection(
        name="test-moonraker",
        connection_type=PrinterConnectionType.MOONRAKER,
        host=host,
        port=port,
    )


def _bambu_conn(
    host: str = "192.168.1.30",
    serial: str = "ABCDEF123456",
    access_code: str = "secret",
) -> PrinterConnection:
    return PrinterConnection(
        name="test-bambu",
        connection_type=PrinterConnectionType.BAMBU,
        host=host,
        serial=serial,
        access_code=access_code,
    )


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Build a minimal mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    # raise_for_status() is a no-op for 2xx; raise for 4xx/5xx
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


def _make_gcode(tmp_path: Path, name: str = "print.gcode") -> Path:
    """Create a minimal G-code file on disk."""
    p = tmp_path / name
    p.write_text("; test gcode\nG28\nM104 S200\n")
    return p


# ===========================================================================
# OctoPrintBackend
# ===========================================================================


class TestOctoPrintConnect:
    """Tests for OctoPrintBackend.connect()."""

    def test_connect_returns_true_on_200_version_response(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(
            json_data={"api": "0.1", "server": "1.9.0"}
        )

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            result = backend.connect()

        assert result is True
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/version" in call_url

    def test_connect_sends_api_key_header(self):
        conn = _octoprint_conn(api_key="my-secret-key")
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response()

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            backend.connect()

        headers = mock_requests.get.call_args[1]["headers"]
        assert headers["X-Api-Key"] == "my-secret-key"

    def test_connect_raises_printer_error_on_connection_error(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.get.side_effect = ConnectionError("Connection refused")

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError) as exc_info:
                backend.connect()

        assert exc_info.value.printer_name == "test-octoprint"

    def test_connect_raises_printer_error_on_http_error(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        bad_resp = _mock_response(status_code=403)
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.HTTPError = Exception
        mock_requests.exceptions.Timeout = TimeoutError
        bad_resp.raise_for_status.side_effect = mock_requests.exceptions.HTTPError("403")
        mock_requests.get.return_value = bad_resp

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.connect()

    def test_connect_raises_printer_error_on_timeout(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.HTTPError = Exception
        mock_requests.exceptions.Timeout = TimeoutError
        mock_requests.get.side_effect = TimeoutError("timed out")

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.connect()

    def test_base_url_uses_configured_port(self):
        """The backend URL includes the configured port."""
        conn = _octoprint_conn(host="printer.local", port=8080)
        backend = OctoPrintBackend(conn)
        assert "8080" in backend._base_url
        assert "printer.local" in backend._base_url

    def test_base_url_defaults_to_port_5000(self):
        conn = PrinterConnection(
            name="no-port",
            connection_type=PrinterConnectionType.OCTOPRINT,
            host="printer.local",
            port=None,
        )
        backend = OctoPrintBackend(conn)
        assert ":5000" in backend._base_url


class TestOctoPrintStatus:
    """Tests for OctoPrintBackend.status()."""

    @pytest.mark.parametrize(
        "state_text,expected_status",
        [
            ("Printing", PrinterStatus.PRINTING),
            ("Paused", PrinterStatus.PAUSED),
            ("Operational", PrinterStatus.IDLE),
            ("Error", PrinterStatus.ERROR),
            ("Offline", PrinterStatus.DISCONNECTED),
            ("Connecting", PrinterStatus.UNKNOWN),
        ],
    )
    def test_status_maps_state_text_correctly(
        self, state_text: str, expected_status: PrinterStatus
    ):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        payload = {
            "state": {"text": state_text},
            "temperature": {
                "tool0": {"actual": 205.0},
                "bed": {"actual": 60.0},
            },
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            info = backend.status()

        assert info.status == expected_status

    def test_status_returns_temperatures(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        payload = {
            "state": {"text": "Operational"},
            "temperature": {
                "tool0": {"actual": 210.5},
                "bed": {"actual": 65.0},
            },
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            info = backend.status()

        assert info.hotend_temp_c == 210.5
        assert info.bed_temp_c == 65.0
        assert info.name == "test-octoprint"
        assert info.connection_type == PrinterConnectionType.OCTOPRINT

    def test_status_handles_missing_temperature_fields_gracefully(self):
        """When temperature data is absent the result still has None values, not an error."""
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        payload = {"state": {"text": "Operational"}, "temperature": {}}
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            info = backend.status()

        assert info.hotend_temp_c is None
        assert info.bed_temp_c is None

    def test_status_hits_printer_endpoint(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(
            json_data={"state": {"text": "Idle"}, "temperature": {}}
        )

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            backend.status()

        call_url = mock_requests.get.call_args[0][0]
        assert "/api/printer" in call_url


class TestOctoPrintUpload:
    """Tests for OctoPrintBackend.upload()."""

    def test_upload_posts_to_files_local(self, tmp_path: Path):
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.post.return_value = _mock_response(status_code=201)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            result = backend.upload(str(gcode))

        assert result is True
        call_url = mock_requests.post.call_args[0][0]
        assert "/api/files/local" in call_url

    def test_upload_sends_file_as_multipart(self, tmp_path: Path):
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.post.return_value = _mock_response(status_code=201)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            backend.upload(str(gcode))

        files_kwarg = mock_requests.post.call_args[1]["files"]
        assert "file" in files_kwarg

    def test_upload_raises_printer_error_for_missing_file(self, tmp_path: Path):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.upload(str(tmp_path / "nonexistent.gcode"))


class TestOctoPrintStartPrint:
    """Tests for OctoPrintBackend.start_print()."""

    def test_start_print_posts_select_command(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        mock_requests.post.return_value = _mock_response(status_code=204)

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            result = backend.start_print("model.gcode")

        assert result is True
        call_url = mock_requests.post.call_args[0][0]
        assert "model.gcode" in call_url
        json_body = mock_requests.post.call_args[1]["json"]
        assert json_body["command"] == "select"
        assert json_body["print"] is True

    def test_start_print_raises_printer_error_on_http_error(self):
        conn = _octoprint_conn()
        backend = OctoPrintBackend(conn)

        mock_requests = MagicMock()
        bad_resp = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.HTTPError = Exception
        mock_requests.exceptions.Timeout = TimeoutError
        bad_resp.raise_for_status.side_effect = mock_requests.exceptions.HTTPError("409 Conflict")
        mock_requests.post.return_value = bad_resp

        with patch(
            "print3d_skill.printing.octoprint._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.start_print("model.gcode")


class TestOctoPrintDisconnect:
    def test_disconnect_is_idempotent(self):
        """disconnect() is a no-op for REST API and should not raise."""
        backend = OctoPrintBackend(_octoprint_conn())
        backend.disconnect()
        backend.disconnect()  # calling twice must not raise


# ===========================================================================
# MoonrakerBackend
# ===========================================================================


class TestMoonrakerConnect:
    """Tests for MoonrakerBackend.connect()."""

    def test_connect_returns_true_on_200_printer_info(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data={"result": {"state": "ready"}})

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            result = backend.connect()

        assert result is True
        call_url = mock_requests.get.call_args[0][0]
        assert "/printer/info" in call_url

    def test_connect_raises_printer_error_on_connection_error(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.get.side_effect = ConnectionError("refused")

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError) as exc_info:
                backend.connect()

        assert exc_info.value.printer_name == "test-moonraker"

    def test_base_url_defaults_to_port_7125(self):
        conn = PrinterConnection(
            name="moon",
            connection_type=PrinterConnectionType.MOONRAKER,
            host="klipper.local",
            port=None,
        )
        backend = MoonrakerBackend(conn)
        assert ":7125" in backend._base_url

    def test_api_key_header_set_when_provided(self):
        conn = _moonraker_conn()
        conn.api_key = "klipper-api-key"
        backend = MoonrakerBackend(conn)
        assert backend._headers.get("X-Api-Key") == "klipper-api-key"

    def test_no_api_key_header_when_absent(self):
        conn = _moonraker_conn()
        conn.api_key = None
        backend = MoonrakerBackend(conn)
        assert "X-Api-Key" not in backend._headers


class TestMoonrakerStatus:
    """Tests for MoonrakerBackend.status()."""

    @pytest.mark.parametrize(
        "state_text,expected_status",
        [
            ("printing", PrinterStatus.PRINTING),
            ("paused", PrinterStatus.PAUSED),
            ("error", PrinterStatus.ERROR),
            ("standby", PrinterStatus.IDLE),
            ("complete", PrinterStatus.IDLE),
            ("shutdown", PrinterStatus.DISCONNECTED),
            ("disconnected", PrinterStatus.DISCONNECTED),
            ("initializing", PrinterStatus.UNKNOWN),
        ],
    )
    def test_status_maps_klipper_state_correctly(
        self, state_text: str, expected_status: PrinterStatus
    ):
        # _parse_moonraker_state is a pure function — test directly
        assert _parse_moonraker_state(state_text) == expected_status

    def test_status_returns_correct_temperatures_and_file(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        payload = {
            "result": {
                "status": {
                    "print_stats": {"state": "printing", "filename": "benchy.gcode"},
                    "extruder": {"temperature": 215.0},
                    "heater_bed": {"temperature": 60.0},
                }
            }
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            info = backend.status()

        assert info.status == PrinterStatus.PRINTING
        assert info.hotend_temp_c == 215.0
        assert info.bed_temp_c == 60.0
        assert info.current_file == "benchy.gcode"
        assert info.name == "test-moonraker"

    def test_status_query_params_include_required_objects(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        payload = {
            "result": {
                "status": {"print_stats": {"state": "standby"}, "extruder": {}, "heater_bed": {}}
            }
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            backend.status()

        call_url = mock_requests.get.call_args[0][0]
        assert "/printer/objects/query" in call_url

    def test_status_handles_empty_print_stats(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        payload = {"result": {"status": {"print_stats": {}, "extruder": {}, "heater_bed": {}}}}
        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(json_data=payload)

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            info = backend.status()

        assert info.status == PrinterStatus.UNKNOWN
        assert info.hotend_temp_c is None
        assert info.bed_temp_c is None


class TestMoonrakerUpload:
    """Tests for MoonrakerBackend.upload()."""

    def test_upload_posts_to_server_files_upload(self, tmp_path: Path):
        gcode = _make_gcode(tmp_path)
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()
        mock_requests.post.return_value = _mock_response(status_code=200)

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            result = backend.upload(str(gcode))

        assert result is True
        call_url = mock_requests.post.call_args[0][0]
        assert "/server/files/upload" in call_url

    def test_upload_raises_printer_error_for_missing_file(self, tmp_path: Path):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.upload(str(tmp_path / "ghost.gcode"))


class TestMoonrakerStartPrint:
    """Tests for MoonrakerBackend.start_print()."""

    def test_start_print_posts_to_correct_endpoint_with_filename_param(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()
        mock_requests.post.return_value = _mock_response(status_code=200)

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            result = backend.start_print("benchy.gcode")

        assert result is True
        call_url = mock_requests.post.call_args[0][0]
        assert "/printer/print/start" in call_url
        params = mock_requests.post.call_args[1]["params"]
        assert params["filename"] == "benchy.gcode"

    def test_start_print_raises_printer_error_on_http_error(self):
        conn = _moonraker_conn()
        backend = MoonrakerBackend(conn)

        mock_requests = MagicMock()
        bad_resp = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.HTTPError = Exception
        mock_requests.exceptions.Timeout = TimeoutError
        bad_resp.raise_for_status.side_effect = mock_requests.exceptions.HTTPError("500")
        mock_requests.post.return_value = bad_resp

        with patch(
            "print3d_skill.printing.moonraker._import_requests", return_value=mock_requests
        ):
            with pytest.raises(PrinterError):
                backend.start_print("benchy.gcode")


class TestMoonrakerDisconnect:
    def test_disconnect_does_not_raise(self):
        backend = MoonrakerBackend(_moonraker_conn())
        backend.disconnect()
        backend.disconnect()


# ===========================================================================
# BambuBackend
# ===========================================================================


class TestBambuConnect:
    """Tests for BambuBackend.connect() via mocked paho-mqtt."""

    def _make_mqtt_mock(self, connect_rc: int = 0) -> MagicMock:
        """Return a mock paho mqtt module whose client triggers _on_connect."""
        mqtt_mod = MagicMock()
        mqtt_mod.MQTTv311 = 4

        client_instance = MagicMock()

        def client_constructor(**kwargs):
            return client_instance

        mqtt_mod.Client.side_effect = lambda **kwargs: client_instance

        # Simulate loop_start triggering the on_connect callback
        def fake_loop_start():
            # Mimic the CONNACK arriving immediately after connect
            if hasattr(client_instance, "_on_connect_callback"):
                client_instance._on_connect_callback(client_instance, None, {}, connect_rc)

        client_instance.loop_start.side_effect = fake_loop_start
        return mqtt_mod, client_instance

    def test_connect_raises_printer_error_when_serial_missing(self):
        conn = _bambu_conn(serial="")
        backend = BambuBackend(conn)

        mock_mqtt = MagicMock()

        with patch("print3d_skill.printing.bambu._import_paho", return_value=mock_mqtt):
            with pytest.raises(PrinterError) as exc_info:
                backend.connect()

        assert (
            "serial" in str(exc_info.value).lower() or "access_code" in str(exc_info.value).lower()
        )

    def test_connect_raises_printer_error_when_access_code_missing(self):
        conn = _bambu_conn(access_code="")
        backend = BambuBackend(conn)

        mock_mqtt = MagicMock()

        with patch("print3d_skill.printing.bambu._import_paho", return_value=mock_mqtt):
            with pytest.raises(PrinterError):
                backend.connect()

    def test_connect_sets_tls_insecure(self):
        """Bambu printers use self-signed certs — TLS must be set insecure."""
        conn = _bambu_conn()
        backend = BambuBackend(conn)

        mock_mqtt = MagicMock()
        client_instance = MagicMock()
        mock_mqtt.Client.return_value = client_instance
        mock_mqtt.MQTTv311 = 4

        # Make connect() block briefly then timeout (we just want to inspect the setup)
        client_instance.connect.side_effect = OSError("refused")

        with patch("print3d_skill.printing.bambu._import_paho", return_value=mock_mqtt):
            with pytest.raises(PrinterError):
                backend.connect()

        client_instance.tls_set.assert_called_once()
        client_instance.tls_insecure_set.assert_called_once_with(True)

    def test_connect_sets_username_with_bblp(self):
        """Bambu auth uses the fixed username 'bblp' and the access_code as password."""
        conn = _bambu_conn(access_code="my-code")
        backend = BambuBackend(conn)

        mock_mqtt = MagicMock()
        client_instance = MagicMock()
        mock_mqtt.Client.return_value = client_instance
        mock_mqtt.MQTTv311 = 4

        client_instance.connect.side_effect = OSError("refused")

        with patch("print3d_skill.printing.bambu._import_paho", return_value=mock_mqtt):
            with pytest.raises(PrinterError):
                backend.connect()

        client_instance.username_pw_set.assert_called_once_with("bblp", "my-code")

    def test_connect_subscribes_to_device_report_topic(self):
        """After connecting, the backend subscribes to device/<serial>/report."""
        conn = _bambu_conn(serial="SN123")
        backend = BambuBackend(conn)

        mock_mqtt = MagicMock()
        client_instance = MagicMock()
        mock_mqtt.Client.return_value = client_instance
        mock_mqtt.MQTTv311 = 4

        # Simulate successful CONNACK by setting _connected in loop_start
        def fake_loop_start():
            backend._connected = True

        client_instance.loop_start.side_effect = fake_loop_start

        with patch("print3d_skill.printing.bambu._import_paho", return_value=mock_mqtt):
            backend.connect()

        client_instance.subscribe.assert_called_once_with("device/SN123/report")

    def test_connect_raises_capability_unavailable_when_paho_missing(self):
        """If paho-mqtt is not installed, _import_paho raises CapabilityUnavailable."""
        conn = _bambu_conn()
        backend = BambuBackend(conn)

        with patch(
            "print3d_skill.printing.bambu._import_paho",
            side_effect=CapabilityUnavailable(
                "printer_control", "paho-mqtt", "pip install paho-mqtt"
            ),
        ):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                backend.connect()

        assert exc_info.value.capability == "printer_control"


class TestBambuStatus:
    """Tests for BambuBackend.status() via mocked MQTT report events."""

    def test_status_raises_printer_error_when_not_connected(self):
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        # _connected is False by default
        with pytest.raises(PrinterError) as exc_info:
            backend.status()

        assert "connect" in str(exc_info.value).lower()

    def test_status_returns_unknown_when_report_event_times_out(self):
        """When no MQTT report arrives within the timeout, UNKNOWN status is returned."""
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._connected = True

        client_mock = MagicMock()
        backend._client = client_mock
        backend._report_event = MagicMock()
        backend._report_event.wait.return_value = False  # simulate timeout

        info = backend.status()

        assert info.status == PrinterStatus.UNKNOWN
        assert info.name == "test-bambu"

    def test_status_publishes_pushall_request(self):
        """status() sends a 'pushall' command to request a fresh status."""
        conn = _bambu_conn(serial="SN999")
        backend = BambuBackend(conn)
        backend._connected = True

        client_mock = MagicMock()
        backend._client = client_mock
        backend._report_event = MagicMock()
        backend._report_event.wait.return_value = False  # timeout is OK for this test

        backend.status()

        client_mock.publish.assert_called_once()
        topic, payload_str = client_mock.publish.call_args[0]
        assert topic == "device/SN999/request"
        import json

        payload = json.loads(payload_str)
        assert payload["pushing"]["command"] == "pushall"

    def test_status_parses_report_from_last_report(self):
        """When a report arrives, it is parsed into a PrinterInfo."""
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._connected = True

        client_mock = MagicMock()
        backend._client = client_mock
        backend._report_event = MagicMock()
        backend._report_event.wait.return_value = True  # report arrived
        backend._last_report = {
            "print": {
                "gcode_state": "RUNNING",
                "nozzle_temper": 215,
                "bed_temper": 65,
                "mc_percent": 42,
                "subtask_name": "benchy.gcode",
            }
        }

        info = backend.status()

        assert info.status == PrinterStatus.PRINTING
        assert info.hotend_temp_c == 215.0
        assert info.bed_temp_c == 65.0
        assert info.progress_percent == 42.0
        assert info.current_file == "benchy.gcode"


class TestBambuParseReport:
    """Unit tests for the pure _parse_bambu_report() function."""

    @pytest.mark.parametrize(
        "gcode_state,expected_status",
        [
            ("IDLE", PrinterStatus.IDLE),
            ("RUNNING", PrinterStatus.PRINTING),
            ("PAUSE", PrinterStatus.PAUSED),
            ("FAILED", PrinterStatus.ERROR),
            ("FINISH", PrinterStatus.IDLE),
            ("UNKNOWN_STATE", PrinterStatus.UNKNOWN),
        ],
    )
    def test_gcode_state_mapping(self, gcode_state: str, expected_status: PrinterStatus):
        report = {"print": {"gcode_state": gcode_state}}
        info = _parse_bambu_report("my-bambu", report)
        assert info.status == expected_status

    def test_empty_report_returns_unknown_status(self):
        info = _parse_bambu_report("my-bambu", {})
        assert info.status == PrinterStatus.UNKNOWN
        assert info.hotend_temp_c is None
        assert info.bed_temp_c is None

    def test_temperatures_converted_to_float(self):
        report = {"print": {"gcode_state": "IDLE", "nozzle_temper": 200, "bed_temper": 60}}
        info = _parse_bambu_report("printer", report)
        assert info.hotend_temp_c == 200.0
        assert info.bed_temp_c == 60.0
        assert isinstance(info.hotend_temp_c, float)
        assert isinstance(info.bed_temp_c, float)

    def test_progress_and_file_extracted(self):
        report = {
            "print": {"gcode_state": "RUNNING", "mc_percent": 75, "subtask_name": "vase.gcode"}
        }
        info = _parse_bambu_report("printer", report)
        assert info.progress_percent == 75.0
        assert info.current_file == "vase.gcode"


class TestBambuUploadAndStartPrint:
    """Tests for BambuBackend.upload() and start_print()."""

    def test_upload_returns_true_when_file_exists(self, tmp_path: Path):
        gcode = _make_gcode(tmp_path)
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._connected = True
        backend._client = MagicMock()

        result = backend.upload(str(gcode))
        assert result is True

    def test_upload_raises_printer_error_when_not_connected(self, tmp_path: Path):
        gcode = _make_gcode(tmp_path)
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        # _connected is False

        with pytest.raises(PrinterError):
            backend.upload(str(gcode))

    def test_upload_raises_printer_error_for_missing_file(self, tmp_path: Path):
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._connected = True
        backend._client = MagicMock()

        with pytest.raises(PrinterError):
            backend.upload(str(tmp_path / "ghost.gcode"))

    def test_start_print_publishes_project_file_command(self):
        conn = _bambu_conn(serial="SN001")
        backend = BambuBackend(conn)
        backend._connected = True

        client_mock = MagicMock()
        backend._client = client_mock

        result = backend.start_print("benchy.gcode")

        assert result is True
        topic, payload_str = client_mock.publish.call_args[0]
        assert topic == "device/SN001/request"
        import json

        payload = json.loads(payload_str)
        assert payload["print"]["command"] == "project_file"
        assert payload["print"]["subtask_name"] == "benchy.gcode"

    def test_start_print_raises_printer_error_when_not_connected(self):
        conn = _bambu_conn()
        backend = BambuBackend(conn)

        with pytest.raises(PrinterError):
            backend.start_print("benchy.gcode")


class TestBambuDisconnect:
    def test_disconnect_stops_loop_and_disconnects_client(self):
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._connected = True

        client_mock = MagicMock()
        backend._client = client_mock

        backend.disconnect()

        client_mock.loop_stop.assert_called_once()
        client_mock.disconnect.assert_called_once()
        assert backend._client is None
        assert backend._connected is False

    def test_disconnect_is_idempotent_when_already_none(self):
        conn = _bambu_conn()
        backend = BambuBackend(conn)
        backend._client = None
        backend.disconnect()  # should not raise


# ===========================================================================
# Config loading
# ===========================================================================


class TestLoadPrinterConfig:
    """Tests for load_printer_config() with a temp YAML file."""

    def test_loads_octoprint_printer_from_yaml(self, tmp_path: Path):
        yaml_content = """\
printers:
  - name: my-octoprint
    type: octoprint
    host: 192.168.1.100
    port: 5000
    api_key: abc123
"""
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert len(connections) == 1
        conn = connections[0]
        assert conn.name == "my-octoprint"
        assert conn.connection_type == PrinterConnectionType.OCTOPRINT
        assert conn.host == "192.168.1.100"
        assert conn.port == 5000
        assert conn.api_key == "abc123"

    def test_loads_moonraker_printer_from_yaml(self, tmp_path: Path):
        yaml_content = """\
printers:
  - name: klipper-voron
    type: moonraker
    host: voron.local
    port: 7125
"""
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert len(connections) == 1
        assert connections[0].connection_type == PrinterConnectionType.MOONRAKER
        assert connections[0].host == "voron.local"

    def test_loads_bambu_printer_from_yaml(self, tmp_path: Path):
        # access_code must be quoted so YAML parses it as a string, not an int
        yaml_content = """\
printers:
  - name: bambu-p1s
    type: bambu
    host: 192.168.1.50
    serial: AABBCCDDEE
    access_code: "12345678"
"""
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert len(connections) == 1
        conn = connections[0]
        assert conn.connection_type == PrinterConnectionType.BAMBU
        assert conn.serial == "AABBCCDDEE"
        assert conn.access_code == "12345678"

    def test_loads_multiple_printers(self, tmp_path: Path):
        yaml_content = """\
printers:
  - name: printer-1
    type: octoprint
    host: 10.0.0.1
  - name: printer-2
    type: moonraker
    host: 10.0.0.2
  - name: printer-3
    type: bambu
    host: 10.0.0.3
    serial: ABC
    access_code: XYZ
"""
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert len(connections) == 3
        names = [c.name for c in connections]
        assert "printer-1" in names
        assert "printer-2" in names
        assert "printer-3" in names

    def test_returns_empty_list_when_file_not_found(self, tmp_path: Path):
        missing = tmp_path / "nonexistent_printers.yaml"

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=missing):
            connections = load_printer_config()

        assert connections == []

    def test_returns_empty_list_when_printers_key_absent(self, tmp_path: Path):
        yaml_content = "other_key: value\n"
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert connections == []

    def test_skips_invalid_printer_entries_without_raising(self, tmp_path: Path):
        """Invalid entries (bad type) are skipped; valid ones are still loaded."""
        yaml_content = """\
printers:
  - name: good-printer
    type: octoprint
    host: 10.0.0.1
  - name: bad-printer
    type: unsupported_protocol
    host: 10.0.0.2
"""
        config_file = tmp_path / "printers.yaml"
        config_file.write_text(yaml_content)

        from print3d_skill.printing.config import load_printer_config

        with patch("print3d_skill.printing.config._config_path", return_value=config_file):
            connections = load_printer_config()

        assert len(connections) == 1
        assert connections[0].name == "good-printer"


# ===========================================================================
# list_printers() — public API
# ===========================================================================


class TestListPrinters:
    """Tests for the list_printers() public function."""

    def test_raises_capability_unavailable_when_config_is_empty(self):
        """If no printers are configured, CapabilityUnavailable is raised."""
        from print3d_skill.printing import list_printers

        with patch("print3d_skill.printing.config.load_printer_config", return_value=[]):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                list_printers()

        assert exc_info.value.capability == "printer_control"

    def test_returns_disconnected_info_when_backend_cannot_connect(self):
        """Printers that fail to connect appear as DISCONNECTED rather than raising."""
        from print3d_skill.printing import list_printers

        conn = _octoprint_conn()
        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.get.side_effect = ConnectionError("refused")

        with (
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
            patch("print3d_skill.printing.octoprint._import_requests", return_value=mock_requests),
        ):
            results = list_printers()

        assert len(results) == 1
        assert results[0].status == PrinterStatus.DISCONNECTED
        assert results[0].name == "test-octoprint"

    def test_returns_printer_info_for_connected_printer(self):
        from print3d_skill.printing import list_printers

        conn = _octoprint_conn()
        mock_requests = MagicMock()
        mock_requests.get.side_effect = [
            # First call: connect() -> GET /api/version
            _mock_response(json_data={"api": "0.1"}),
            # Second call: status() -> GET /api/printer
            _mock_response(
                json_data={
                    "state": {"text": "Operational"},
                    "temperature": {"tool0": {"actual": 200.0}, "bed": {"actual": 60.0}},
                }
            ),
        ]

        with (
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
            patch("print3d_skill.printing.octoprint._import_requests", return_value=mock_requests),
        ):
            results = list_printers()

        assert len(results) == 1
        assert results[0].status == PrinterStatus.IDLE


# ===========================================================================
# _find_printer() — internal helper
# ===========================================================================


class TestFindPrinter:
    """Tests for the _find_printer() internal function."""

    def test_raises_printer_error_for_unknown_name(self):
        from print3d_skill.printing import _find_printer

        connections = [_octoprint_conn(), _moonraker_conn()]

        with pytest.raises(PrinterError) as exc_info:
            _find_printer(connections, "nonexistent-printer")

        assert exc_info.value.printer_name == "nonexistent-printer"

    def test_returns_connection_for_matching_name(self):
        from print3d_skill.printing import _find_printer

        target = _octoprint_conn()
        other = _moonraker_conn()

        result = _find_printer([target, other], "test-octoprint")

        assert result is target

    def test_error_message_lists_available_printers(self):
        from print3d_skill.printing import _find_printer

        conn_a = _octoprint_conn()
        conn_b = _moonraker_conn()

        with pytest.raises(PrinterError) as exc_info:
            _find_printer([conn_a, conn_b], "mystery-printer")

        error_msg = str(exc_info.value)
        assert "test-octoprint" in error_msg
        assert "test-moonraker" in error_msg


# ===========================================================================
# submit_print() — validation gate
# ===========================================================================


class TestSubmitPrintValidationGate:
    """Tests for submit_print() ValidationError enforcement."""

    def test_raises_validation_error_when_validate_gcode_returns_fail(self, tmp_path: Path):
        """submit_print() must raise ValidationError when validation status is FAIL."""
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()

        fail_result = ValidationResult(
            status=ValidationStatus.FAIL,
            failures=["Hotend temperature 340°C exceeds max 300°C"],
        )

        from print3d_skill.printing import submit_print

        with (
            patch("print3d_skill.validate.validate_gcode", return_value=fail_result),
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
        ):
            with pytest.raises(ValidationError) as exc_info:
                submit_print(str(gcode), printer_name="test-octoprint")

        assert exc_info.value.validation_result is fail_result
        assert "Hotend temperature" in str(exc_info.value)

    def test_does_not_contact_printer_when_validation_fails(self, tmp_path: Path):
        """No HTTP requests are made when validation returns FAIL."""
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()

        fail_result = ValidationResult(
            status=ValidationStatus.FAIL,
            failures=["Critical error"],
        )

        mock_requests = MagicMock()

        from print3d_skill.printing import submit_print

        with (
            patch("print3d_skill.validate.validate_gcode", return_value=fail_result),
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
            patch("print3d_skill.printing.octoprint._import_requests", return_value=mock_requests),
        ):
            with pytest.raises(ValidationError):
                submit_print(str(gcode), printer_name="test-octoprint")

        # HTTP methods should never have been called
        mock_requests.get.assert_not_called()
        mock_requests.post.assert_not_called()

    def test_raises_file_not_found_before_validation(self, tmp_path: Path):
        """FileNotFoundError is raised before even calling validate_gcode."""
        mock_validate = MagicMock()

        from print3d_skill.printing import submit_print

        with patch("print3d_skill.validate.validate_gcode", mock_validate):
            with pytest.raises(FileNotFoundError):
                submit_print(str(tmp_path / "nonexistent.gcode"), printer_name="any")

        mock_validate.assert_not_called()

    def test_submit_print_succeeds_when_validation_passes(self, tmp_path: Path):
        """When validation passes (PASS), the print job is submitted."""
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()

        pass_result = ValidationResult(status=ValidationStatus.PASS)

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(
            json_data={"state": {"text": "Operational"}, "temperature": {}}
        )
        mock_requests.post.return_value = _mock_response(status_code=204)

        from print3d_skill.printing import submit_print

        with (
            patch("print3d_skill.validate.validate_gcode", return_value=pass_result),
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
            patch("print3d_skill.printing.octoprint._import_requests", return_value=mock_requests),
        ):
            job = submit_print(str(gcode), printer_name="test-octoprint")

        assert job.submitted is True
        assert job.printer_name == "test-octoprint"
        assert job.validation_result is pass_result

    def test_submit_print_with_warn_validation_still_proceeds(self, tmp_path: Path):
        """WARN validation status should not block the print."""
        gcode = _make_gcode(tmp_path)
        conn = _octoprint_conn()

        warn_result = ValidationResult(
            status=ValidationStatus.WARN,
            warnings=["Speed slightly high"],
        )

        mock_requests = MagicMock()
        mock_requests.get.return_value = _mock_response(
            json_data={"state": {"text": "Operational"}, "temperature": {}}
        )
        mock_requests.post.return_value = _mock_response(status_code=204)

        from print3d_skill.printing import submit_print

        with (
            patch("print3d_skill.validate.validate_gcode", return_value=warn_result),
            patch("print3d_skill.printing.config.load_printer_config", return_value=[conn]),
            patch("print3d_skill.printing.octoprint._import_requests", return_value=mock_requests),
        ):
            job = submit_print(str(gcode), printer_name="test-octoprint")

        assert job.submitted is True
