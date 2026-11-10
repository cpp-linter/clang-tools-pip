"""Tests of ``clang-tools list``."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from clang_tools import MAX_VERSION, MIN_VERSION, listing, suffix
from clang_tools.install import install_clang_tools, platform_name
from clang_tools.listing import (
    Installed,
    available_tools,
    installed_tools,
    tool_version,
)
from clang_tools.main import main
from clang_tools.util import PyPIFallback

from conftest import RELEASED_TOOLS, FakeRelease


@pytest.fixture
def not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `install_clang_tools()` find no tool in ``PATH``."""
    monkeypatch.setattr(
        "clang_tools.install.is_installed", lambda tool, ver, directory=None: None
    )


def fake_run(output: bytes):
    """A stand-in for ``subprocess.run`` whose tools print *output*."""

    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr=b"")

    return run


def test_tool_version_reads_what_the_tool_prints(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        subprocess, "run", fake_run(b"Ubuntu clang-format version 21.1.8\n")
    )
    assert tool_version(Path("clang-format-21")) == "21.1.8"


def test_tool_version_of_a_file_that_prints_no_version(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(subprocess, "run", fake_run(b"hello\n"))
    assert tool_version(Path("clang-format-21")) is None


def test_tool_version_of_a_file_that_does_not_run(tmp_path: Path):
    assert tool_version(tmp_path / "missing") is None


@pytest.mark.usefixtures("not_installed")
def test_installed_tools(
    monkeypatch: pytest.MonkeyPatch, fake_release: FakeRelease, tmp_path: Path
):
    """A static binary, a wheel and a file put there by something else."""
    fake_release.add_wheel("clang-format", "10.0.1.1")
    monkeypatch.setattr("clang_tools.wheel_install.is_compatible", lambda tag: True)
    install_clang_tools(
        "21", ["clang-tidy", "clang-format"], str(tmp_path), False, True
    )
    install_clang_tools("10", ["clang-format"], str(tmp_path), False, True)
    (tmp_path / f"clang-query-9{suffix}").write_bytes(b"from another installer")
    # not versioned clang tools
    (tmp_path / f"clang-21{suffix}").write_bytes(b"the compiler")
    (tmp_path / "notes.txt").write_text("notes")
    (tmp_path / f"llvm-cov-21{suffix}").mkdir()
    # the fake tools can't be run, so the major version is shown
    assert installed_tools(str(tmp_path)) == [
        Installed(
            "clang-format",
            "10",
            "wheel",
            False,
            str(tmp_path.resolve() / f"clang-format-10{suffix}"),
        ),
        Installed(
            "clang-format",
            "21",
            "binary",
            True,
            str(tmp_path.resolve() / f"clang-format-21{suffix}"),
        ),
        Installed(
            "clang-query",
            "9",
            "copy",
            False,
            str(tmp_path.resolve() / f"clang-query-9{suffix}"),
        ),
        Installed(
            "clang-tidy",
            "21",
            "binary",
            True,
            str(tmp_path.resolve() / f"clang-tidy-21{suffix}"),
        ),
    ]


def test_installed_tools_shows_the_version_a_tool_prints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    (tmp_path / f"clang-format-21{suffix}").write_bytes(b"binary")
    monkeypatch.setattr(listing, "tool_version", lambda path: "21.1.8")
    assert [tool.version for tool in installed_tools(str(tmp_path))] == ["21.1.8"]


def test_installed_tools_in_a_directory_that_does_not_exist(tmp_path: Path):
    assert installed_tools(str(tmp_path / "missing")) == []


def test_available_tools():
    available = available_tools()
    assert [entry["major"] for entry in available] == list(
        range(MAX_VERSION, MIN_VERSION - 1, -1)
    )
    assert available[0]["tools"] == sorted(RELEASED_TOOLS)


def test_available_tools_leaves_out_other_platforms(fake_release: FakeRelease):
    fake_release.index = {
        "schema_version": 1,
        "versions": {
            "21": {
                "version": "21.1.8",
                "tools": {
                    "clang-format": {platform_name(): {}},
                    "clang-tidy": {"other-platform": {}},
                },
            },
            "9": {"tools": {}},
        },
    }
    assert available_tools() == [
        {"major": 21, "version": "21.1.8", "tools": ["clang-format"]},
        {"major": 9, "version": "9", "tools": []},
    ]


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------


def run_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["clang-tools", *args])
    return main()


@pytest.mark.usefixtures("not_installed")
def test_main_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    install_clang_tools("21", ["clang-format"], str(tmp_path), False, True)
    install_clang_tools("20", ["clang-apply-replacements"], str(tmp_path), False, True)
    capsys.readouterr()
    assert run_main(monkeypatch, "list", "-d", str(tmp_path)) == 0
    directory = tmp_path.resolve()
    assert capsys.readouterr().out.splitlines() == [
        f"Tools in {directory}:",
        "  clang-apply-replacements  20  binary  default  "
        + str(directory / f"clang-apply-replacements-20{suffix}"),
        "  clang-format              21  binary  default  "
        + str(directory / f"clang-format-21{suffix}"),
    ]


def test_main_list_nothing_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    assert run_main(monkeypatch, "list", "--directory", str(tmp_path)) == 0
    assert capsys.readouterr().out == f"No clang tools in {tmp_path.resolve()}\n"


def test_main_list_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    path = tmp_path.resolve() / f"clang-tidy-18{suffix}"
    path.write_bytes(b"binary")
    assert run_main(monkeypatch, "list", "-d", str(tmp_path), "--json") == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "tool": "clang-tidy",
            "version": "18",
            "source": "copy",
            "default": False,
            "path": str(path),
        }
    ]


def test_main_list_available(monkeypatch: pytest.MonkeyPatch, capsys):
    assert run_main(monkeypatch, "list", "--available") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"Static binaries for {platform_name()}:"
    assert len(lines) == 2 + MAX_VERSION - MIN_VERSION
    assert lines[1].split(maxsplit=1)[1] == ", ".join(sorted(RELEASED_TOOLS))


def test_main_list_available_json(monkeypatch: pytest.MonkeyPatch, capsys):
    assert run_main(monkeypatch, "list", "-a", "--json") == 0
    assert json.loads(capsys.readouterr().out) == available_tools()


def test_main_list_available_without_the_index(monkeypatch: pytest.MonkeyPatch, capsys):
    def no_index():
        raise PyPIFallback("Failed to download the index")

    monkeypatch.setattr("clang_tools.main.available_tools", no_index)
    assert run_main(monkeypatch, "list", "--available") == 1
    assert "Failed to download the index" in capsys.readouterr().err
