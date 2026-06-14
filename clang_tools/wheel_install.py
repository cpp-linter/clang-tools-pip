"""
``clang_tools.wheel_install``
-----------------------------

Self-contained wheel installation via PyPI.

Tool versions are resolved dynamically from the PyPI JSON API —
no hardcoded version list is maintained in-tree.
"""

import json
import logging
import re
import shutil
import subprocess
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

LOG = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _get_pypi_versions(tool: str) -> Tuple[Optional[str], list]:
    """Fetch (latest_version, [stable_versions_descending]) from PyPI JSON API.

    Results are cached per tool name so repeated calls within the same
    process reuse the last HTTP response.
    """
    try:
        url = f"https://pypi.org/pypi/{tool}/json"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
    except Exception as exc:
        LOG.warning("Failed to fetch versions for %s from PyPI: %s", tool, exc)
        return None, []

    all_versions = list(data["releases"].keys())

    # Filter out pre-release versions
    pre_release_pattern = re.compile(
        r".*(alpha|beta|rc|dev|a\d+|b\d+).*", re.IGNORECASE
    )
    stable = [v for v in all_versions if not pre_release_pattern.match(v)]

    if not stable:
        LOG.warning("No stable versions found for %s on PyPI", tool)
        return None, []

    # Sort ascending by version tuple
    stable.sort(key=lambda x: tuple(map(int, x.split("."))))

    latest = stable[-1]
    # Return descending for prefix matching (newest first)
    return latest, list(reversed(stable))


def _detect_installed_version(tool: str) -> Optional[str]:
    """Return the version of *tool* already on PATH, or None.

    Used as a fallback when PyPI is unreachable and no explicit version
    was requested.  Extracts the version string from ``<tool> --version``
    output (e.g. ``"clang-format version 18.1.8"`` → ``"18.1.8"``).
    """
    existing = shutil.which(tool)
    if not existing:
        return None
    try:
        result = subprocess.run(
            [existing, "--version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"(\d+\.\d+\.\d+(?:\.\d+)?)", result.stdout)
    return match.group(1) if match else None


def _resolve_version(
    tool: str, user_input: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a version dynamically from PyPI.

    Returns (resolved_version, error_message). The error_message is
    suitable for displaying directly to the end user.

    When PyPI is unreachable and no explicit version was requested,
    falls back to whatever version is already installed on the host
    so that pre-installed tools keep working offline.
    """
    latest, versions = _get_pypi_versions(tool)

    if not versions:
        if user_input is None:
            installed = _detect_installed_version(tool)
            if installed:
                LOG.info(
                    "PyPI unreachable; using locally installed %s %s",
                    tool,
                    installed,
                )
                return installed, None
        return (
            None,
            f"Could not find any stable versions of {tool} on PyPI. "
            "Check your network connection.",
        )

    if user_input is None:
        return latest, None

    # Exact match
    if user_input in versions:
        return user_input, None

    # Prefix match (e.g. "20" → "20.1.8"). Versions are newest-first,
    # so the first matching entry is the latest for that prefix.
    matched = [v for v in versions if v.startswith(user_input)]
    if matched:
        return matched[0], None

    # No match – help the user
    sample = ", ".join(versions[:15])
    return (
        None,
        f"Unsupported {tool} version '{user_input}'.\n"
        f"Latest stable version: {latest}\n"
        f"Available versions (sample): {sample}\n"
        f"Run `pip index versions {tool}` to see all available versions.",
    )


def _is_version_installed(tool: str, version: str) -> Optional[Path]:
    """Return the tool path if the installed version matches, otherwise None."""
    existing = shutil.which(tool)
    if not existing:
        return None
    result = subprocess.run([existing, "--version"], capture_output=True, text=True)
    if version in result.stdout:
        return Path(existing)
    return None


def _install_tool(tool: str, version: str) -> Optional[Path]:
    """Install a tool using pip, logging output on failure."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", f"{tool}=={version}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return shutil.which(tool)
    LOG.error("pip failed to install %s %s", tool, version)
    LOG.error(result.stdout)
    LOG.error(result.stderr)
    return None


def resolve_wheel_install(
    tool: str, version: Optional[str]
) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve and install a clang tool as a Python wheel from PyPI.

    Tool versions are resolved dynamically from the PyPI JSON API —
    no hardcoded list is maintained in-tree.

    :param tool: Tool name as registered on PyPI (e.g. ``"clang-format"``).
    :param version: Desired version string, or ``None`` for the latest stable.

    :returns: A tuple ``(path, error)`` where *path* is the installed
        binary location on success and *error* is a user-facing message
        on failure. Exactly one of the two is not ``None``.
    """
    user_version, error = _resolve_version(tool, version)
    if error is not None:
        return None, error

    return (
        _is_version_installed(tool, user_version) or _install_tool(tool, user_version),
        None,
    )
