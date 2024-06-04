"""
``clang_tools.util``
-----------------------

A module containing utility functions.
"""

import platform
import hashlib
from pathlib import Path
import urllib.request
from typing import Optional, Tuple
from urllib.error import HTTPError
from http.client import HTTPResponse


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
        raise SystemExit(f"{this_os} is not currently supported")
    return this_os


def download_file(url: str, file_name: str, no_progress_bar: bool) -> Optional[str]:
    """Download the given file_name from the given url.

    :param url: The URL to download from.
    :param file_name: The file name to download.

    :returns: The path to downloaded file if  successful, otherwise `None`.
    """
    try:
        response: HTTPResponse = urllib.request.urlopen(url)
    except (ValueError, HTTPError):
        return None

    if response.status != 200:
        return None
    assert response.length is not None
    length = response.length
    buffer = b""
    progress_bar = "=" if check_install_os() == "windows" else "█"
    while len(buffer) < length:
        block_size = int(length / 20)
        if not no_progress_bar:  # show completed
            percent = len(buffer) / length
            completed = int(percent * 20)
            display = "    |" + (progress_bar * completed)
            display += " " * (20 - completed) + "| "
            display += f"{int(percent * 100)}% (of {length} bytes)"
            reset_pos = "" if not buffer else "\033[F"
            print(reset_pos + display)
        remaining = length - len(buffer)
        buffer += response.read(block_size if remaining > block_size else remaining)
    response.close()
    if not no_progress_bar:
        display = f"    |{(progress_bar * 20)}| 100% (of {length} bytes)"
        print("\033[F" + display)
    file = Path(file_name)
    file.write_bytes(buffer)
    return file.as_posix()


def get_sha_checksum(binary_url: str) -> str:
    """Fetch the SHA512 checksum corresponding to the released binary.

    :param binary_url: The URL used to download the binary.

    :returns: A `str` containing the contents of the SHA512sum file given
        ``binary_url``.
    """
    with urllib.request.urlopen(
        binary_url.replace(".exe", "") + ".sha512sum"
    ) as response:
        return response.read(response.length).decode(encoding="utf-8")


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


class Version:
    """Parse the given version string into a semantic specification.

    :param user_input: The version specification as a string.
    """

    def __init__(self, user_input: str):
        #: The version input in string form
        self.string = user_input
        version_tuple = user_input.split(".")
        self.info: Tuple[int, int, int]
        """
        A tuple of integers that describes the major, minor, and patch versions.
        If the version `string` is a path, then this tuple is just 3 zeros.
        """
        if len(version_tuple) < 3:
            # append minor and patch version numbers if not specified
            version_tuple += ["0"] * (3 - len(version_tuple))
        try:
            self.info = tuple([int(x) for x in version_tuple])  # type: ignore[assignment]
        except ValueError:
            self.info = (0, 0, 0)
