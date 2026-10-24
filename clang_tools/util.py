"""
``clang_tools.util``
-----------------------

A module containing utility functions.
"""

import hashlib
import json
import platform
import re
import urllib.request
from functools import cache
from http.client import HTTPException, HTTPResponse
from pathlib import Path

#: Seconds to wait for the server to accept the connection or send more data.
DOWNLOAD_TIMEOUT = 30
#: The errors a failed download can raise. An invalid URL or a response that can't be
#: decoded is a ValueError. HTTP errors, timeouts and dropped connections are OSErrors.
#: A malformed HTTP response is an http.client.HTTPException.
DOWNLOAD_ERRORS = (ValueError, OSError, HTTPException)


class PyPIFallback(Exception):
    """The static binary can't be installed, so the wheel from PyPI is tried instead.

    Raise this only for failures where installing the wheel is a sensible next step,
    such as a version or tool that has no static binary, or a download that failed.
    When it is caused by another exception, raise it ``from`` that exception. Any
    other error stops the ``clang-tools install`` command.
    """


def check_install_arch() -> str:
    """Identify the CPU architecture.

    :returns: ``"amd64"`` for x86-64 and ``"arm64"`` for 64-bit ARM processors, as in
        the static binaries' file names. Any other architecture keeps its own name in
        lower case, such as ``"ppc64le"``, ``"s390x"`` or ``"i686"``. No static binary
        is built for those, so only wheels can be installed on them.
    """
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64", "x64"):
        return "amd64"
    if machine in ("i386", "i486", "i586", "i686", "x86"):
        return "i686"
    return machine


def check_install_os() -> str:
    """Identify this Operating System.

    .. note::
        This will raise an exception if the detected OS is not supported.
        Please open an issue at https://github.com/cpp-linter/clang-tools-pip/issues
        if you encounter an unsupported OS.

    :returns: A lower-case `str` describing the detected OS.
    """
    this_os = platform.system().lower()
    if this_os == "darwin":
        this_os = "macosx"
    if this_os not in ["linux", "macosx", "windows"]:
        raise OSError(f"{this_os} is not currently supported")
    return this_os


def download_file(
    url: str,
    file_name: str,
    no_progress_bar: bool,
    headers: dict[str, str] | None = None,
) -> str:
    """Download the given file_name from the given url.

    :param url: The URL to download from.
    :param file_name: The file name to download.
    :param headers: HTTP headers to send, such as ``Authorization``. They are sent to
        ``url`` only, not to where it redirects.

    :returns: The path to downloaded file.
    :raises PyPIFallback: If the file could not be downloaded completely.
    """
    try:
        request = urllib.request.Request(url)
        for name, value in (headers or {}).items():
            request.add_unredirected_header(name, value)  # not sent to a redirect
        response: HTTPResponse = urllib.request.urlopen(
            request, timeout=DOWNLOAD_TIMEOUT
        )
    except DOWNLOAD_ERRORS as exc:
        raise PyPIFallback(f"Failed to download {url}: {exc}") from exc

    if response.status != 200:
        response.close()
        raise PyPIFallback(f"Failed to download {url}: HTTP status {response.status}")
    assert response.length is not None
    length = response.length
    buffer = b""
    progress_bar = "=" if check_install_os() == "windows" else "█"
    while len(buffer) < length:
        block_size = max(int(length / 20), 1)
        if not no_progress_bar:  # show completed
            percent = len(buffer) / length
            completed = int(percent * 20)
            display = "    |" + (progress_bar * completed)
            display += " " * (20 - completed) + "| "
            display += f"{int(percent * 100)}% (of {length} bytes)"
            reset_pos = "" if not buffer else "\033[F"
            print(reset_pos + display)
        remaining = length - len(buffer)
        try:
            data = response.read(min(remaining, block_size))
        except DOWNLOAD_ERRORS as exc:
            response.close()
            raise PyPIFallback(f"Failed to download {url}: {exc}") from exc
        if not data:  # the connection closed before the whole file arrived
            response.close()
            raise PyPIFallback(
                f"Failed to download {url}: the connection closed after"
                f" {len(buffer)} of {length} bytes"
            )
        buffer += data
    response.close()
    if not no_progress_bar:
        display = f"    |{(progress_bar * 20)}| 100% (of {length} bytes)"
        print("\033[F" + display)
    file = Path(file_name)
    file.write_bytes(buffer)
    return file.as_posix()


#: The ``schema_version`` of ``index.json`` that this package understands.
INDEX_SCHEMA_VERSION = 1


@cache
def fetch_index(url: str) -> dict:
    """Fetch and cache the static binaries' ``index.json``.

    :param url: The URL of the index.

    :returns: The parsed index.
    :raises PyPIFallback: If the index could not be downloaded or is not usable.
    """
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            index = json.loads(response.read().decode(encoding="utf-8"))
    except DOWNLOAD_ERRORS as exc:  # invalid JSON is a ValueError too
        raise PyPIFallback(f"Failed to download the index from {url}: {exc}") from exc
    if not isinstance(index, dict):
        raise PyPIFallback(f"The index at {url} is not a JSON object.")
    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise PyPIFallback(
            f"Unsupported index schema version {index.get('schema_version')!r}"
            f" at {url}. Please upgrade clang-tools."
        )
    if not isinstance(index.get("versions"), dict):
        raise PyPIFallback(f"The index at {url} has no versions.")
    if not all(major.isdecimal() for major in index["versions"]):
        raise PyPIFallback(f"The index at {url} has a version that is not a number.")
    return index


@cache
def _fetch_sha512sums(sha_url: str) -> str:
    """Fetch and cache the SHA512SUMS file content.

    :param sha_url: The URL of the SHA512SUMS file.

    :returns: The content of the SHA512SUMS file as a string.
    """
    with urllib.request.urlopen(sha_url, timeout=DOWNLOAD_TIMEOUT) as response:
        return response.read().decode(encoding="utf-8")


def get_sha_checksum(binary_url: str) -> str:
    """Fetch the SHA512 checksum corresponding to the released binary.

    Checksums are stored in a single ``SHA512SUMS`` file at the release root.
    This function fetches that file and parses it to find the hash for the
    specific binary identified by *binary_url*.

    :param binary_url: The URL used to download the binary.

    :returns: A `str` containing the SHA512 checksum (hash only) for the
        given binary.
    :raises PyPIFallback: If ``SHA512SUMS`` could not be downloaded or does not list
        the binary.
    """
    # Extract the binary filename from the URL (last path segment)
    bin_filename = binary_url.rsplit("/", 1)[-1]

    # Build the SHA512SUMS URL (same base URL, different file)
    base_url = binary_url.rsplit("/", 1)[0]
    sha_url = f"{base_url}/SHA512SUMS"

    try:
        content = _fetch_sha512sums(sha_url)
    except DOWNLOAD_ERRORS as exc:
        raise PyPIFallback(f"Failed to download {sha_url}: {exc}") from exc

    # Parse SHA512SUMS to find the line matching our binary.
    # Format: "<sha512hash>  <filename>" (hash and filename separated
    # by two spaces).
    for line in content.splitlines():
        line = line.strip()
        parts = line.rsplit("  ", 1)
        if len(parts) == 2 and parts[1] == bin_filename:
            return parts[0]

    raise PyPIFallback(
        f"Could not find SHA512 checksum for {bin_filename} in SHA512SUMS"
    )


def verify_sha512(checksum: str, exe: bytes) -> bool:
    """Verify the executable binary's SHA512 hash matches the valid checksum.

    :param checksum: The SHA512 checksum.
    :param exe: The `bytes` content of the binary executable that is to be verified.

    :returns: `True` if the ``exe`` hash matches the ``checksum`` given,
        otherwise `False`.
    """
    if " " in checksum:
        # released checksum's include the corresponding filename (which we don't need)
        checksum = checksum.split(" ", 1)[0]
    return checksum == hashlib.sha512(exe).hexdigest()


#: A release version made of numbers only, such as ``21`` or ``21.1.8``.
RE_VERSION = re.compile(r"\d+(\.\d+)*", re.ASCII)


def major_version(version: str) -> str:
    """The major version of a version, such as ``21`` for ``21.1.8``."""
    return version.split(".", 1)[0]


def version_key(version: str) -> tuple[int, ...]:
    """The numbers of a version, to sort or compare versions such as ``21.1.8``."""
    return tuple(map(int, version.split(".")))


def version_matches(wanted: str, actual: str) -> bool:
    """Check if ``actual`` is the version ``wanted``, which may omit numbers.

    For example, ``21`` and ``21.1`` match ``21.1.8``, but ``21.1.0`` and ``2``
    don't.
    """
    return actual.split(".")[: wanted.count(".") + 1] == wanted.split(".")
