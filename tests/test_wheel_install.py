"""Tests for clang_tools.wheel_install — PyPI version resolution and pip installation."""

import json
import subprocess
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clang_tools.wheel_install import (
    _get_pypi_versions,
    _detect_installed_version,
    _resolve_version,
    _is_version_installed,
    _install_tool,
    resolve_wheel_install,
)


def _pypi_response(releases: dict) -> MagicMock:
    """Build a mock HTTP response that works as a context manager for urlopen."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"releases": releases})
    resp.__enter__.return_value = resp
    return resp


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the LRU cache on _get_pypi_versions between tests."""
    _get_pypi_versions.cache_clear()
    yield
    _get_pypi_versions.cache_clear()


# ---------------------------------------------------------------------------
#  _get_pypi_versions
# ---------------------------------------------------------------------------


def test_get_pypi_versions_success():
    """Fetch versions from a mocked PyPI JSON response."""
    resp = _pypi_response(
        {
            "18.1.8": [],
            "19.1.0": [],
            "19.1.1": [],
            "20.1.0": [],
            "20.1.8": [],
            "20.1.3rc1": [],  # pre-release — filtered
            "21.0.0.dev1": [],  # dev — filtered
            "21.1.0": [],
            "21.1.1": [],
            "22.0.0a1": [],  # alpha — filtered
        }
    )

    with patch.object(urllib.request, "urlopen", return_value=resp):
        latest, versions = _get_pypi_versions("clang-format")

    assert latest == "21.1.1"
    assert versions == [
        "21.1.1",
        "21.1.0",
        "20.1.8",
        "20.1.0",
        "19.1.1",
        "19.1.0",
        "18.1.8",
    ]
    assert "20.1.3rc1" not in versions
    assert "21.0.0.dev1" not in versions
    assert "22.0.0a1" not in versions


def test_get_pypi_versions_network_error():
    """When PyPI is unreachable, return (None, [])."""
    with patch.object(
        urllib.request, "urlopen", side_effect=urllib.request.URLError("timeout")
    ):
        latest, versions = _get_pypi_versions("clang-format")
    assert latest is None
    assert versions == []


def test_get_pypi_versions_no_stable():
    """When only pre-release versions exist, return (None, [])."""
    resp = _pypi_response({"1.0.0alpha": [], "1.0.0b1": [], "1.0.0rc1": []})

    with patch.object(urllib.request, "urlopen", return_value=resp):
        latest, versions = _get_pypi_versions("clang-format")

    assert latest is None
    assert versions == []


def test_get_pypi_versions_cached():
    """LRU cache reuses the first result on repeated calls."""
    call_count = 0

    def counting_urlopen(url, timeout=None):
        nonlocal call_count
        call_count += 1
        return _pypi_response({"1.0.0": [], "2.0.0": []})

    with patch.object(urllib.request, "urlopen", side_effect=counting_urlopen):
        result1 = _get_pypi_versions("clang-format")
        result2 = _get_pypi_versions("clang-format")
        result3 = _get_pypi_versions("clang-tidy")  # different tool → new call

    assert call_count == 2
    assert result1 == result2


# ---------------------------------------------------------------------------
#  _detect_installed_version
# ---------------------------------------------------------------------------


def test_detect_installed_version_found():
    """Detect version from ``<tool> --version`` output."""
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="clang-format version 18.1.8\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        version = _detect_installed_version("clang-format")
    assert version == "18.1.8"


def test_detect_installed_version_not_found():
    """Return None when tool is not on PATH."""
    with patch("shutil.which", return_value=None):
        version = _detect_installed_version("clang-format")
    assert version is None


def test_detect_installed_version_subprocess_error():
    """Return None when subprocess fails."""
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(subprocess, "run", side_effect=OSError("bad")),
    ):
        version = _detect_installed_version("clang-format")
    assert version is None


def test_detect_installed_version_no_version_in_output():
    """Return None when --version output has no recognizable version."""
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="unknown output\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        version = _detect_installed_version("clang-format")
    assert version is None


# ---------------------------------------------------------------------------
#  _resolve_version
# ---------------------------------------------------------------------------


def test_resolve_version_null_input():
    """When user_input is None, return the latest stable version."""
    resp = _pypi_response({"18.1.8": [], "19.1.0": [], "20.1.8": []})

    with patch.object(urllib.request, "urlopen", return_value=resp):
        resolved, error = _resolve_version("clang-format", None)

    assert resolved == "20.1.8"
    assert error is None


def test_resolve_version_exact_match():
    """When user_input exactly matches an available version."""
    resp = _pypi_response({"18.1.8": [], "19.1.0": [], "20.1.8": []})

    with patch.object(urllib.request, "urlopen", return_value=resp):
        resolved, error = _resolve_version("clang-format", "18.1.8")

    assert resolved == "18.1.8"
    assert error is None


def test_resolve_version_prefix_match():
    """Prefix match picks the newest version starting with the prefix."""
    resp = _pypi_response(
        {
            "18.1.8": [],
            "19.1.0": [],
            "19.1.1": [],
            "19.1.7": [],
            "20.1.8": [],
        }
    )

    with patch.object(urllib.request, "urlopen", return_value=resp):
        resolved, error = _resolve_version("clang-format", "19")

    assert resolved == "19.1.7"
    assert error is None


def test_resolve_version_no_match():
    """When no version matches, return an error message."""
    resp = _pypi_response({"18.1.8": [], "19.1.0": []})

    with patch.object(urllib.request, "urlopen", return_value=resp):
        resolved, error = _resolve_version("clang-format", "999")

    assert resolved is None
    assert error is not None
    assert "Unsupported" in error
    assert "Latest stable version" in error
    assert "pip index versions" in error


def test_resolve_version_pypi_unreachable_no_input():
    """When PyPI is unreachable and user gives no version, fall back to local."""
    with (
        patch.object(
            urllib.request, "urlopen", side_effect=urllib.request.URLError("timeout")
        ),
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="clang-format version 18.1.8\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        resolved, error = _resolve_version("clang-format", None)

    assert resolved == "18.1.8"
    assert error is None


def test_resolve_version_pypi_unreachable_no_local():
    """When PyPI is unreachable AND no local tool, return error."""
    with (
        patch.object(
            urllib.request, "urlopen", side_effect=urllib.request.URLError("timeout")
        ),
        patch("shutil.which", return_value=None),
    ):
        resolved, error = _resolve_version("clang-format", None)

    assert resolved is None
    assert error is not None
    assert "Could not find any stable versions" in error


def test_resolve_version_pypi_unreachable_with_version():
    """When PyPI is unreachable and user specified a version, return error."""
    with patch.object(
        urllib.request, "urlopen", side_effect=urllib.request.URLError("timeout")
    ):
        resolved, error = _resolve_version("clang-format", "18.1.8")

    assert resolved is None
    assert error is not None
    assert "Could not find any stable versions" in error


# ---------------------------------------------------------------------------
#  _is_version_installed
# ---------------------------------------------------------------------------


def test_is_version_installed_found():
    """Return path when installed version matches."""
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="clang-format version 18.1.8\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        path = _is_version_installed("clang-format", "18.1.8")
    assert path == Path("/usr/bin/clang-format")


def test_is_version_installed_not_on_path():
    """Return None when tool is not found."""
    with patch("shutil.which", return_value=None):
        path = _is_version_installed("clang-format", "18.1.8")
    assert path is None


def test_is_version_installed_wrong_version():
    """Return None when the installed version does not match."""
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="clang-format version 19.1.0\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        path = _is_version_installed("clang-format", "18.1.8")
    assert path is None


# ---------------------------------------------------------------------------
#  _install_tool
# ---------------------------------------------------------------------------


def test_install_tool_success():
    """Successful pip install returns the tool path."""
    with (
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(returncode=0, spec=subprocess.CompletedProcess),
        ),
        patch("shutil.which", return_value="/usr/bin/clang-format"),
    ):
        path = _install_tool("clang-format", "18.1.8")
    assert path == "/usr/bin/clang-format"


def test_install_tool_failure():
    """Failed pip install returns None."""
    with patch.object(
        subprocess,
        "run",
        return_value=MagicMock(
            returncode=1,
            stdout="error",
            stderr="pip error",
            spec=subprocess.CompletedProcess,
        ),
    ):
        path = _install_tool("clang-format", "18.1.8")
    assert path is None


# ---------------------------------------------------------------------------
#  resolve_wheel_install (integration / public API)
# ---------------------------------------------------------------------------


def test_resolve_wheel_install_success():
    """Full successful resolution and install."""
    resp = _pypi_response({"18.1.8": [], "20.1.8": []})

    with (
        patch.object(urllib.request, "urlopen", return_value=resp),
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="clang-format version 18.1.8\n",
                spec=subprocess.CompletedProcess,
            ),
        ),
    ):
        path, error = resolve_wheel_install("clang-format", "18.1.8")

    assert path == Path("/usr/bin/clang-format")
    assert error is None


def test_resolve_wheel_install_latest():
    """Install the latest stable version when version is None."""
    resp = _pypi_response({"18.1.8": [], "20.1.8": []})

    with (
        patch.object(urllib.request, "urlopen", return_value=resp),
        patch("shutil.which", side_effect=[None, "/usr/bin/clang-format"]),
        patch.object(
            subprocess,
            "run",
            return_value=MagicMock(returncode=0, spec=subprocess.CompletedProcess),
        ),
    ):
        path, error = resolve_wheel_install("clang-format", None)

    assert path == "/usr/bin/clang-format"
    assert error is None


def test_resolve_wheel_install_version_error():
    """Returns error when version cannot be resolved."""
    resp = _pypi_response({"18.1.8": []})

    with patch.object(urllib.request, "urlopen", return_value=resp):
        path, error = resolve_wheel_install("clang-format", "999")

    assert path is None
    assert error is not None
    assert "Unsupported" in error
