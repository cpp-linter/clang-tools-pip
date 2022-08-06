"""Tests related to the utility functions."""
from pathlib import Path
import pytest
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import check_install_os
from clang_tools.util import download_file
from clang_tools.util import unpack_file


def test_check_install_os():
    """Tests the return value of `check_install_os()`."""
    install_os = check_install_os()
    assert install_os in ("linux", "windows", "macosx")


@pytest.mark.parametrize(
    "tag", ["master-208096c1", pytest.param("latest", marks=pytest.mark.xfail)]
)
def test_download_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tag: str):
    """Test that deliberately fails to download a file."""
    monkeypatch.chdir(str(tmp_path))
    url = clang_tools_binary_url("clang-query", "12", release_tag=tag)
    file_name = download_file(url, "file.tar.gz")
    assert file_name is not None


def test_unpack_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test `unpack_file()` on a dummy archive saved to the tests directory"""
    monkeypatch.chdir(str(tmp_path))
    assert unpack_file(str(Path(__file__).parent / "file.tar.gz"))
