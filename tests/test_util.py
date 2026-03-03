"""Tests related to the utility functions."""

from pathlib import Path, PurePath
import pytest
from clang_tools import install_arch, install_os
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import (
    check_install_arch,
    check_install_os,
    download_file,
    get_sha_checksum,
    Version,
)


def test_check_install_os():
    """Tests the return value of `check_install_os()`."""
    current_os = check_install_os()
    assert current_os in ("linux", "windows", "macosx")


def test_check_install_arch():
    """Tests the return value of `check_install_arch()`."""
    current_arch = check_install_arch()
    assert current_arch in ("amd64", "arm64")


def test_download_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that deliberately fails to download a file."""
    monkeypatch.chdir(str(tmp_path))
    url = clang_tools_binary_url("clang-format", "21")
    file_name = download_file(url, "file.tar.gz", True)
    assert file_name is not None


def test_get_sha(monkeypatch: pytest.MonkeyPatch):
    """Test the get_sha() function used to fetch the
    releases' corresponding SHA512 checksum."""
    monkeypatch.chdir(PurePath(__file__).parent.as_posix())
    if install_os == "macosx":
        platform_str = (
            "macosx-arm64" if install_arch == "arm64" else "macos-intel-amd64"
        )
    else:
        platform_str = f"{install_os}-amd64"
    expected = Path(f"clang-format-21_{platform_str}.sha512sum").read_text(
        encoding="utf-8"
    )
    url = clang_tools_binary_url("clang-format", "21")
    assert get_sha_checksum(url) == expected


def test_version_path():
    """Tests version parsing when given specification is a path."""
    version = str(Path(__file__).parent)
    assert Version(version).info == (0, 0, 0)
