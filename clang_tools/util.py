"""A module containing utility functions."""
import platform
from typing import Optional
import tarfile
import urllib.request
from urllib.error import HTTPError


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
    if this_os not in ['linux', 'macosx', 'windows']:
        raise SystemExit(f"{this_os} is not currently supported")
    return this_os


def download_file(url: str, file_name: str) -> Optional[str]:
    """Download the given file_name from the given url.

    :returns: The path to downloaded file if  successful, otherwise `None`.
    """
    try:
        file, _ = urllib.request.urlretrieve(url, file_name)
    except (ValueError, HTTPError):
        return None
    return file


def unpack_file(file_name: str) -> bool:
    """Unpacks the archive."""
    if tarfile.is_tarfile(file_name):
        file = tarfile.open(file_name)
        file.extractall()
        file.close()
        return True
    return False
