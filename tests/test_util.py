"""Tests related to the utility functions."""

from pathlib import Path, PurePath
import pytest
from clang_tools import install_os
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import check_install_os, download_file, get_sha_checksum, Version
from clang_tools import binary_tag


def test_check_install_os():
    """Tests the return value of `check_install_os()`."""
    current_os = check_install_os()
    assert current_os in ("linux", "windows", "macosx")


@pytest.mark.parametrize(
    "tag", [binary_tag, pytest.param("latest", marks=pytest.mark.xfail)]
)
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
    expected = Path(f"clang-format-21_{install_os}-amd64.sha512sum").read_text(
        encoding="utf-8"
    )
    url = clang_tools_binary_url("clang-format", "21", tag=binary_tag)
    assert get_sha_checksum(url) == expected


def test_version_path():
    """Tests version parsing when given specification is a path."""
    version = str(Path(__file__).parent)
    assert Version(version).info == (0, 0, 0)
