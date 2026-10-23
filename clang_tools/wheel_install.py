"""
``clang_tools.wheel_install``
-----------------------------

Install a clang tool from its wheel on PyPI, without pip.

The wheel is downloaded from the PyPI JSON API, checked against its SHA256 checksum,
and its ``<package>/data`` folder (``bin/`` and, for clang-tidy, ``lib/clang/``) is
kept in the data directory, like a static binary. The install directory gets a link
to the executable.
"""

import hashlib
import json
import platform
import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from . import install_arch, install_os, pypi_url, suffix
from .install import binary_file_name, data_dir, link_binary, make_dir
from .util import (
    DOWNLOAD_ERRORS,
    DOWNLOAD_TIMEOUT,
    RE_VERSION,
    PyPIFallback,
    download_file,
    major_version,
    version_matches,
)

#: The glibc versions of the legacy ``manylinux`` tags.
LEGACY_MANYLINUX = {
    "manylinux1": (2, 5),
    "manylinux2010": (2, 12),
    "manylinux2014": (2, 17),
}
RE_MANYLINUX = re.compile(r"(manylinux|musllinux)_(\d+)_(\d+)_(\w+)")
RE_MACOSX = re.compile(r"macosx_(\d+)_(\d+)_(\w+)")


def _major_minor(version: str) -> tuple[int, ...]:
    """The first two numbers of a version, such as ``(2, 39)`` for glibc 2.39.

    A missing or unparsable version is ``(0,)``.
    """
    return tuple(int(n) for n in re.findall(r"\d+", version)[:2]) or (0,)


def is_compatible(tag: str) -> bool:
    """Check if a wheel's platform tag (such as ``win_amd64``) runs on this machine."""
    if install_os == "windows":
        return tag == f"win_{install_arch}"
    if install_os == "macosx":
        match = RE_MACOSX.fullmatch(tag)
        arch = "arm64" if install_arch == "arm64" else "x86_64"
        return (
            match is not None
            and match[3] in (arch, "universal2")
            and (int(match[1]), int(match[2])) <= _major_minor(platform.mac_ver()[0])
        )
    arch = "aarch64" if install_arch == "arm64" else "x86_64"
    libc, libc_version = platform.libc_ver()
    glibc = libc == "glibc"
    legacy, _, legacy_arch = tag.partition("_")
    if legacy in LEGACY_MANYLINUX:
        return (
            glibc
            and legacy_arch == arch
            and (LEGACY_MANYLINUX[legacy] <= _major_minor(libc_version))
        )
    match = RE_MANYLINUX.fullmatch(tag)
    if match is None or match[4] != arch:
        return False
    if match[1] == "musllinux":
        return not glibc
    return glibc and (int(match[2]), int(match[3])) <= _major_minor(libc_version)


def pypi_releases(tool: str) -> dict[str, list[dict]]:
    """The stable releases of a tool on PyPI, with their files.

    :param tool: The name of the project on PyPI, such as ``clang-format``.

    :returns: The files of each release that only has numbers in its version.
    """
    url = f"{pypi_url}/{tool}/json"
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            releases = json.loads(response.read().decode(encoding="utf-8"))["releases"]
    except (*DOWNLOAD_ERRORS, KeyError, TypeError) as exc:
        raise SystemExit(f"Can't get the releases of {tool} from {url}: {exc}") from exc
    return {
        version: files
        for version, files in releases.items()
        if RE_VERSION.fullmatch(version) and isinstance(files, list)
    }


def find_wheel(tool: str, version: str | None) -> tuple[str, dict]:
    """Find the newest wheel of a tool that runs on this machine.

    :param tool: The name of the project on PyPI.
    :param version: The version to install, such as ``21`` or ``21.1.8``, or `None`
        for the newest one.

    :returns: The version and the file information (from the PyPI JSON API) of the
        wheel.
    """
    releases = pypi_releases(tool)
    candidates = sorted(
        (v for v in releases if version is None or version_matches(version, v)),
        key=lambda v: tuple(map(int, v.split("."))),
        reverse=True,
    )
    for candidate in candidates:
        for file in releases[candidate]:
            filename = file.get("filename", "")
            if file.get("yanked") or not filename.endswith(".whl"):
                continue
            tags = filename.removesuffix(".whl").rsplit("-", 1)[-1].split(".")
            if any(is_compatible(tag) for tag in tags):
                return candidate, file
    wanted = f"{tool} {version}" if version else tool
    raise SystemExit(
        f"No wheel of {wanted} on PyPI runs on this machine"
        f" ({install_os} {install_arch})."
    )


def extract_wheel(wheel: Path, package: str, destination: Path) -> None:
    """Extract the ``bin/`` and ``lib/`` folders of a wheel's ``<package>/data``.

    :param wheel: The wheel file.
    :param package: The import name of the package, such as ``clang_format``.
    :param destination: The directory to extract into.
    """
    prefix = f"{package}/data/"
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            parts = PurePosixPath(info.filename.removeprefix(prefix)).parts
            if parts[0] not in ("bin", "lib"):
                continue
            if ".." in parts:
                raise SystemExit(f"Unexpected entry {info.filename!r} in {wheel.name}")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            if parts[0] == "bin":
                target.chmod(0o755)


def install_wheel(
    tool: str, version: str | None, directory: str, no_progress_bar: bool
) -> str:
    """Install a tool from its wheel on PyPI, in the same way as a static binary.

    :param tool: The name of the tool, which is also its project name on PyPI.
    :param version: The version to install, such as ``21`` or ``21.1.8``, or `None`
        for the newest one.
    :param directory: The installation directory.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :returns: The installed version.
    """
    try:
        binary_file_name(tool, "0")  # the tool name must be a plain file name
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    resolved, file = find_wheel(tool, version)
    prefix = data_dir() / f"pypi-{tool}-{resolved}"
    exe = prefix / "bin" / f"{tool}{suffix}"
    if not exe.is_file():
        make_dir(data_dir())
        with tempfile.TemporaryDirectory(dir=data_dir()) as work_dir:
            wheel = Path(work_dir, f"{tool}.whl")
            try:
                download_file(file["url"], str(wheel), no_progress_bar)
            except PyPIFallback as exc:
                raise SystemExit(str(exc)) from exc
            checksum = hashlib.sha256(wheel.read_bytes()).hexdigest()
            if checksum != file.get("digests", {}).get("sha256"):
                raise SystemExit(
                    f"{file['filename']} was corrupted during download from"
                    f" {file['url']}"
                )
            extracted = Path(work_dir, "extracted")
            extract_wheel(wheel, tool.replace("-", "_"), extracted)
            if not (extracted / "bin" / exe.name).is_file():
                raise SystemExit(f"{file['filename']} has no {exe.name} executable.")
            try:
                # one rename, so the directory is either complete or not there
                extracted.rename(prefix)
            except OSError:
                if not exe.is_file():
                    raise  # pragma: no cover (not a parallel install)
    destination = Path(directory, binary_file_name(tool, major_version(resolved)))
    link_binary(exe, destination)
    print(f"Installed {tool} {resolved} (from PyPI) as {destination}")
    return resolved
