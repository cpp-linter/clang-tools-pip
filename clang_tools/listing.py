"""
``clang_tools.listing``
-----------------------

The module that lists the clang tools that are installed or can be installed.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from . import index_url, suffix
from .install import (
    RE_PARSE_VERSION,
    data_dir,
    install_dir_name,
    is_wheel,
    platform_name,
)
from .util import fetch_index

#: An installed tool's file name, such as ``clang-format-21``: a clang or LLVM tool
#: name and a major version (``clang-21``, the compiler, is not one).
RE_INSTALLED = re.compile(
    r"((?:clang|llvm)-[a-z]+(?:-[a-z]+)*)-(\d+)" + re.escape(suffix)
)


class Installed(NamedTuple):
    """A tool found in the install directory."""

    #: The name of the tool, such as ``clang-format``.
    tool: str
    #: The version that the tool prints, such as ``21.1.8``, or only the major
    #: version when the tool can't be run.
    version: str
    #: Where the tool comes from: ``binary`` (a static binary in the data
    #: directory), ``wheel`` (a wheel in the data directory) or ``copy`` (a file
    #: in the install directory itself, or a link to somewhere else).
    source: str
    #: Whether the unversioned name, such as ``clang-format``, runs this version.
    default: bool
    #: The path of the tool in the install directory.
    path: str


def tool_version(path: Path) -> str | None:
    """Ask a tool for its version.

    :returns: The version that ``<path> --version`` prints, or `None` if the tool
        can't be run or prints no version.
    """
    try:
        result = subprocess.run(
            [str(path), "--version"], capture_output=True, check=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = RE_PARSE_VERSION.search(result.stdout)
    return None if match is None else match[1].decode(encoding="utf-8")


def tool_source(path: Path) -> str:
    """Tell where an installed tool comes from (see `Installed.source`)."""
    resolved = path.resolve()
    if not resolved.is_relative_to(data_dir()):
        return "copy"
    return "wheel" if is_wheel(resolved) else "binary"


def installed_tools(directory: str) -> list[Installed]:
    """Find the versioned clang tools in an install directory.

    :param directory: The install directory, or an empty string for the default one.

    :returns: The tools, ordered by name and then by version.
    """
    install_dir = Path(install_dir_name(directory))
    try:
        names = os.listdir(install_dir)
    except OSError:  # nothing was installed there yet
        return []
    found = []
    for name in names:
        match = RE_INSTALLED.fullmatch(name)
        path = install_dir / name
        if match is None or not path.is_file():
            continue
        tool, major = match[1], match[2]
        link = install_dir / f"{tool}{suffix}"
        found.append(
            (
                tool,
                int(major),
                Installed(
                    tool,
                    tool_version(path) or major,
                    tool_source(path),
                    link.exists() and link.samefile(path),
                    str(path),
                ),
            )
        )
    return [item for _, _, item in sorted(found)]


def available_tools() -> list[dict]:
    """The static binaries that can be installed on this platform.

    :returns: For each LLVM version in the index, newest first, its major version,
        its full version and the names of the tools built for this platform.
    :raises PyPIFallback: If the index could not be downloaded or is not usable.
    """
    versions = fetch_index(index_url)["versions"]
    platform = platform_name()
    return [
        {
            "major": int(major),
            "version": versions[major].get("version", major),
            "tools": sorted(
                tool
                for tool, binaries in versions[major]["tools"].items()
                if platform in binaries
            ),
        }
        for major in sorted(versions, key=int, reverse=True)
    ]
