"""Tests related to installing a clang tool."""
from pathlib import PurePath, Path
import os
import pytest
from clang_tools import install_os, suffix
from clang_tools.install import (
    is_installed,
    clang_tools_binary_url,
    install_dir_name,
    create_sym_link,
    install_tool,
)


@pytest.mark.parametrize("version", ["", pytest.param("1", marks=pytest.mark.xfail)])
@pytest.mark.parametrize("tool_name", ["clang-format", "clang-tidy"])
def test_clang_tools_exist(tool_name: str, version: str):
    """Test `is_installed()`"""
    assert is_installed(tool_name, version)


@pytest.mark.parametrize("version", [str(v) for v in range(7, 14)] + ["12.0.1"])
@pytest.mark.parametrize("tool_name", ["clang-format", "clang-tidy"])
def test_clang_tools_binary_url(tool_name: str, version: str):
    """Test `clang_tools_binary_url()`"""
    url = clang_tools_binary_url(tool_name, version)
    assert f"{tool_name}-{version}_{install_os}-amd64" in url


@pytest.mark.parametrize("directory", ["", "."])
def test_dir_name(monkeypatch: pytest.MonkeyPatch, directory: str):
    """Test install directory name generation."""
    monkeypatch.chdir(str(PurePath(__file__).parent))
    install_dir = install_dir_name(directory)
    assert PurePath(install_dir).is_absolute()


def test_create_symlink(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test creation of symlink."""
    tool_name, version = ("clang-tool", "1")
    monkeypatch.chdir(str(tmp_path))
    # use a test tar file and rename it to "clang-tool-1" (+ OS suffix)
    test_target = tmp_path / f"{tool_name}-{version}{suffix}"
    test_target.write_bytes(b"some binary data")

    # create the symlink
    assert create_sym_link(tool_name, version, str(tmp_path), False)
    # intentionally fail to overwrite symlink
    assert not create_sym_link(tool_name, version, str(tmp_path), False)
    # intentionally overwrite symlink
    assert create_sym_link(tool_name, version, str(tmp_path), True)

    # test safegaurd that doesn't overwrite a file that isn't a symlink
    os.remove(str(tmp_path / f"{tool_name}{suffix}"))
    Path(tmp_path / f"{tool_name}{suffix}").write_bytes(b"som data")
    assert not create_sym_link(tool_name, version, str(tmp_path), True)


@pytest.mark.parametrize("version", [str(v) for v in range(10, 14)] + ["12.0.1"])
@pytest.mark.parametrize("overwrite", [False, True])
def test_install_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, version: str, overwrite: bool):
    """Test install tools to a temp directory."""
    monkeypatch.chdir(tmp_path)
    for tool_name in ("clang-format", "clang-tidy"):
        install_tool(tool_name, version, str(tmp_path), overwrite)
