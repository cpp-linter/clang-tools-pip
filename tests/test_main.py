"""Tests that relate to the unified main.py CLI."""

import sys
from argparse import ArgumentParser

import pytest

from clang_tools import MAX_VERSION, suffix
from clang_tools.main import get_parser, main

# ---------------------------------------------------------------------------
#  Parser – install subcommand
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> ArgumentParser:
    return get_parser()


def test_install_subcommand_defaults(parser: ArgumentParser):
    """Default values for the ``install`` subcommand."""
    args = parser.parse_args(["install", "clang-format"])
    assert args.command == "install"
    assert args.tools == ["clang-format"]
    assert args.explicit_version is None
    assert args.directory == ""
    assert args.overwrite is False
    assert args.no_progress_bar is False


def test_install_subcommand_multiple_tools(parser: ArgumentParser):
    args = parser.parse_args(["install", "clang-format", "clang-tidy"])
    assert args.tools == ["clang-format", "clang-tidy"]


def test_install_subcommand_with_version(parser: ArgumentParser):
    args = parser.parse_args(["install", "clang-format", "--version", "18"])
    assert args.explicit_version == "18"


def test_install_subcommand_directory(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--version", "18", "-d", "/custom/path"]
    )
    assert args.directory == "/custom/path"


def test_install_subcommand_flags(parser: ArgumentParser):
    args = parser.parse_args(
        [
            "install",
            "clang-format",
            "--version",
            "18",
            "--overwrite",
            "--no-progress-bar",
        ]
    )
    assert args.overwrite is True
    assert args.no_progress_bar is True


def test_uninstall_subcommand(parser: ArgumentParser):
    args = parser.parse_args(["uninstall", "clang-format", "--version", "12"])
    assert args.command == "uninstall"
    assert args.tools == ["clang-format"]
    assert args.version == "12"
    assert args.directory == ""


def test_uninstall_subcommand_multiple_tools(parser: ArgumentParser):
    args = parser.parse_args(
        ["uninstall", "clang-format", "clang-tidy", "--version", "12"]
    )
    assert args.tools == ["clang-format", "clang-tidy"]


# ---------------------------------------------------------------------------
#  Integration / functional tests – ``install`` subcommand
# ---------------------------------------------------------------------------


def test_main_no_args(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools`` with no args prints help."""
    monkeypatch.setattr(sys, "argv", ["clang-tools"])
    exit_code = main()
    result = capsys.readouterr()
    assert "Nothing to do" in result.err
    assert exit_code == 0


def test_main_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools --version`` prints package version."""
    monkeypatch.setattr(sys, "argv", ["clang-tools", "--version"])
    exit_code = main()
    result = capsys.readouterr()
    assert "clang-tools" in result.out
    assert exit_code == 0


def test_main_version_short(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools -V`` prints package version."""
    monkeypatch.setattr(sys, "argv", ["clang-tools", "-V"])
    exit_code = main()
    result = capsys.readouterr()
    assert "clang-tools" in result.out
    assert exit_code == 0


def test_main_version_subcommand(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools version`` prints package version."""
    monkeypatch.setattr(sys, "argv", ["clang-tools", "version"])
    exit_code = main()
    result = capsys.readouterr()
    assert "clang-tools" in result.out
    assert exit_code == 0


def test_main_version_does_not_conflict_with_install(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path
):
    """``clang-tools install --version 12`` still works (not confused with root --version)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "--version",
            "12",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_with_version_success(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path
):
    """Auto-detect with --version tries binary first (succeeds)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "--version",
            "12",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_multiple_tools(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path):
    """Auto-detect: multiple tool names with --version."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "clang-tidy",
            "--version",
            "12",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    for tool in ("clang-format", "clang-tidy"):
        bin_path = tmp_path / f"{tool}-12{suffix}"
        assert bin_path.exists()


# ---- ``uninstall`` subcommand -----------------------------------------


def test_main_uninstall_subcommand(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys):
    """``clang-tools uninstall clang-format --version 12`` removes installed tools."""
    tool_name = "clang-format"
    version = "12"
    install_dir = str(tmp_path)
    dummy_bin = tmp_path / f"{tool_name}-{version}{suffix}"
    dummy_bin.write_bytes(b"dummy")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "uninstall",
            tool_name,
            "--version",
            version,
            "--directory",
            install_dir,
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "Uninstalling" in result.out
    assert not dummy_bin.exists()


def test_main_uninstall_multiple_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
    """``clang-tools uninstall clang-format clang-tidy --version 12``."""
    version = "12"
    install_dir = str(tmp_path)
    for tool in ("clang-format", "clang-tidy"):
        dummy = tmp_path / f"{tool}-{version}{suffix}"
        dummy.write_bytes(b"dummy")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "uninstall",
            "clang-format",
            "clang-tidy",
            "--version",
            version,
            "--directory",
            install_dir,
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "Uninstalling" in result.out
    for tool in ("clang-format", "clang-tidy"):
        assert not (tmp_path / f"{tool}-{version}{suffix}").exists()


def test_main_uninstall_arguments(monkeypatch: pytest.MonkeyPatch):
    """``uninstall`` passes the tools, version and directory through."""
    calls: list = []
    monkeypatch.setattr(
        "clang_tools.main.uninstall_clang_tools", lambda *args: calls.append(args)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "uninstall", "clang-format", "--version", "15", "-d", "x"],
    )
    assert main() == 0
    assert calls == [(["clang-format"], "15", "x")]


def test_main_version_output(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools version`` prints the version of the clang-tools package."""
    queried: list = []

    def fake_version(name: str) -> str:
        queried.append(name)
        return "1.2.3"

    monkeypatch.setattr("importlib.metadata.version", fake_version)
    monkeypatch.setattr(sys, "argv", ["clang-tools", "version"])
    assert main() == 0
    assert capsys.readouterr().out == "clang-tools 1.2.3\n"
    assert queried == ["clang-tools"]


# ---- ``install`` subcommand: what is passed on ------------------------


def test_main_install_options(monkeypatch: pytest.MonkeyPatch):
    """The install gets every CLI option."""
    calls: list = []
    monkeypatch.setattr(
        "clang_tools.main.install_clang_tools", lambda *args: calls.append(args)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "clang-tidy",
            "--version",
            "18.1.8",
            "-d",
            "some/dir",
            "-f",
            "-b",
        ],
    )
    assert main() == 0
    assert calls == [("18.1.8", ["clang-format", "clang-tidy"], "some/dir", True, True)]


def test_main_install_no_version(monkeypatch: pytest.MonkeyPatch):
    """Without --version, the newest version is installed."""
    calls: list = []
    monkeypatch.setattr(
        "clang_tools.main.install_clang_tools", lambda *args: calls.append(args)
    )
    monkeypatch.setattr(sys, "argv", ["clang-tools", "install", "clang-tidy"])
    assert main() == 0
    assert calls == [(None, ["clang-tidy"], "", False, False)]


@pytest.mark.parametrize("version", ["/usr/lib/llvm-18/bin", "18.x", "", "v18"])
def test_main_install_invalid_version(
    monkeypatch: pytest.MonkeyPatch, capsys, version: str
):
    """A version that isn't made of numbers is an error, before any download."""
    monkeypatch.setattr(
        "clang_tools.main.install_clang_tools",
        lambda *args: pytest.fail("nothing should be installed"),
    )
    monkeypatch.setattr(
        sys, "argv", ["clang-tools", "install", "clang-format", "--version", version]
    )
    assert main() == 1
    assert f"Invalid version {version!r}" in capsys.readouterr().err


def test_main_install_newest_binary(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Without --version, any tool in the index installs its newest binary."""
    monkeypatch.setattr("clang_tools.install.is_installed", lambda tool, ver: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-query", "-d", str(tmp_path), "-b"],
    )
    assert main() == 0
    assert (tmp_path / f"clang-query-{MAX_VERSION}{suffix}").is_symlink()
