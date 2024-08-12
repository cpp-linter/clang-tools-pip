"""Tests related to installing a clang tool."""
from pathlib import PurePath, Path
import os
import pytest
from clang_tools import install_os, suffix
from clang_tools.install import (
    clang_tools_binary_url,
    install_dir_name,
    create_sym_link,
    install_tool,
    install_clang_tools,
    is_installed,
    uninstall_clang_tools,
)
from clang_tools.util import Version


@pytest.mark.parametrize("version", [str(v) for v in range(7, 17)] + ["12.0.1"])
@pytest.mark.parametrize(
    "tool_name",
    ["clang-format", "clang-tidy", "clang-query", "clang-apply-replacements"],
)
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

    # test safeguard that doesn't overwrite a file that isn't a symlink
    os.remove(str(tmp_path / f"{tool_name}{suffix}"))
    Path(tmp_path / f"{tool_name}{suffix}").write_bytes(b"som data")
    assert not create_sym_link(tool_name, version, str(tmp_path), True)


@pytest.mark.parametrize(
    "tool_name",
    ["clang-format", "clang-tidy", "clang-query", "clang-apply-replacements"],
)
@pytest.mark.parametrize("version", ["12"])
def test_install_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool_name: str, version: str
):
    """Test install tools to a temp directory."""
    monkeypatch.chdir(tmp_path)
    assert install_tool(tool_name, version, str(tmp_path), False)
    # invoking again should return False
    assert not install_tool(tool_name, version, str(tmp_path), False)
    # uninstall the tool deliberately
    uninstall_clang_tools(tool_name, version, str(tmp_path))
    assert f"{tool_name}-{version}{suffix}" in [fd.name for fd in tmp_path.iterdir()]


@pytest.mark.parametrize("version", ["0"])
def test_is_installed(version: str):
    """Test if installed version matches specified ``version``"""
    tool_path = is_installed("clang-format", version=Version(version))
    assert tool_path is None


def test_path_warning(capsys: pytest.CaptureFixture):
    """Explicitly fail to download a set of tools to test the prompts that

    1. warns users about using a dir not in env var PATH.
    2. indicates a failure to download a tool
    """
    try:
        install_clang_tools(Version("0"), "x", ".", False, False)
    except OSError as exc:
        if install_dir_name(".") not in os.environ.get("PATH", ""):  # pragma: no cover
            # this warning does not happen in an activated venv
            result = capsys.readouterr()
            assert "directory is not in your environment variable PATH" in result.out
        assert "Failed to download" in exc.args[0]
