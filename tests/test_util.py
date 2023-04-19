"""Tests related to the utility functions."""
from pathlib import Path, PurePath
import pytest
from clang_tools import install_os
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import check_install_os, download_file, get_sha_checksum


def test_check_install_os():
    """Tests the return value of `check_install_os()`."""
    current_os = check_install_os()
    assert current_os in ("linux", "windows", "macosx")


@pytest.mark.parametrize(
    "tag", ["master-9ba48406", pytest.param("latest", marks=pytest.mark.xfail)]
)
def test_download_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tag: str):
    """Test that deliberately fails to download a file."""
    monkeypatch.chdir(str(tmp_path))
    url = clang_tools_binary_url("clang-query", "12", release_tag=tag)
    file_name = download_file(url, "file.tar.gz", True)
    assert file_name is not None


def test_get_sha(monkeypatch: pytest.MonkeyPatch):
    """Test the get_sha() function used to fetch the
    releases' corresponding SHA512 checksum."""
    monkeypatch.chdir(PurePath(__file__).parent.as_posix())
    expected = Path(f"clang-query-12_{install_os}-amd64.sha512sum").read_text(
        encoding="utf-8"
    )
    url = clang_tools_binary_url("clang-query", "12", release_tag="master-9ba48406")
    assert get_sha_checksum(url) == expected
