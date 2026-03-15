"""Unit tests for the skill router (US4).

Tests mode dispatch, stub responses, error handling, and system_info.
"""

from __future__ import annotations

import pytest

from print3d_skill import route, system_info
from print3d_skill.exceptions import InvalidModeError


class TestValidModes:
    def test_diagnose_mode_returns_response(self):
        """Diagnose mode is implemented — returns error when defects missing."""
        response = route("diagnose")
        assert response.mode == "diagnose"
        assert response.status == "error"
        assert "defects" in response.message.lower()

    def test_modify_mode_returns_response(self):
        """Modify mode is implemented — returns error when mesh_path is missing."""
        response = route("modify")
        assert response.mode == "modify"
        assert response.status == "error"
        assert "mesh_path" in response.message

    def test_fix_mode_returns_response(self):
        """Fix mode is implemented — returns error when mesh_path is missing."""
        response = route("fix")
        assert response.mode == "fix"
        assert response.status == "error"
        assert "mesh_path" in response.message

    def test_create_mode_returns_response(self):
        """Create mode is implemented — returns error when description is missing."""
        response = route("create")
        assert response.mode == "create"
        assert response.status == "error"
        assert "description" in response.message

    def test_validate_mode_returns_response(self, minimal_gcode_path):
        """Validate mode is implemented — returns success for valid G-code."""
        response = route("validate", gcode_path=str(minimal_gcode_path))
        assert response.mode == "validate"
        assert response.status == "success"

    @pytest.mark.parametrize("mode", ["create", "fix", "modify", "diagnose", "validate"])
    def test_stub_responses_include_mode_name(self, mode):
        response = route(mode)
        assert response.mode == mode


class TestInvalidModes:
    def test_invalid_mode_raises_error(self):
        with pytest.raises(InvalidModeError) as exc_info:
            route("invalid_mode")
        assert "invalid_mode" in str(exc_info.value)

    def test_error_lists_valid_modes(self):
        with pytest.raises(InvalidModeError) as exc_info:
            route("bad")
        msg = str(exc_info.value)
        for valid in ("create", "fix", "modify", "diagnose", "validate"):
            assert valid in msg

    def test_empty_string_raises_error(self):
        with pytest.raises(InvalidModeError):
            route("")


class TestSystemInfo:
    def test_returns_system_info(self):
        info = system_info()
        assert info.package_version == "0.1.0"
        assert info.python_version

    def test_core_available(self):
        info = system_info()
        assert info.core_available is True

    def test_capabilities_populated(self):
        info = system_info()
        assert len(info.capabilities) > 0
        names = {c.name for c in info.capabilities}
        assert "mesh_loading" in names

    def test_extended_categorized(self):
        info = system_info()
        # OpenSCAD caps should be in either available or missing
        all_ext = set(info.extended_available) | set(info.missing_extended)
        assert "cad_compilation" in all_ext
