"""Tests that relate to the main.py module."""

from typing import Optional, List
from argparse import ArgumentParser
import sys
import pytest
from clang_tools import suffix
from clang_tools.main import get_parser, main


class Args:
    """A pseudo namespace for testing argparse.
    These class attributes are set to the CLI args default values."""

    directory: str = ""
    install: Optional[str] = None
    overwrite: bool = False
    no_progress_bar: bool = False
    uninstall: Optional[str] = None
    tool: List[str] = ["clang-format", "clang-tidy"]


@pytest.fixture
def parser() -> ArgumentParser:
    """get the arg parser for the tests in this module."""
    return get_parser()


@pytest.mark.parametrize("arg_name", ["install", "directory", "uninstall"])
@pytest.mark.parametrize("arg_value", [str(v) for v in range(7, 17)] + ["12.0.1"])
def test_arg_parser(arg_name: str, arg_value: str, parser: ArgumentParser):
    """Test CLI arg parsing using a set of fake args."""
    args = parser.parse_args([f"--{arg_name}={arg_value}"])
    assert getattr(args, arg_name) == arg_value


@pytest.mark.parametrize("switch_name", ["overwrite", "no-progress-bar"])
def test_cli_switch(switch_name: str, parser: ArgumentParser):
    """Test the CLI switches/flags"""
    args = parser.parse_args([f"--{switch_name}"])
    assert getattr(args, switch_name.replace("-", "_"))


def test_default_args(parser: ArgumentParser):
    """Test the default values of CLI args"""
    args = parser.parse_args([])
    for name, value in args.__dict__.items():
        assert getattr(Args, name) == value


def test_main_uninstall(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys):
    """Test main() with --uninstall flag."""
    # Create a dummy bin to uninstall
    tool_name = "clang-format"
    version = "12"
    install_dir = str(tmp_path)
    dummy_bin = tmp_path / f"{tool_name}-{version}{suffix}"
    dummy_bin.write_bytes(b"dummy")

    monkeypatch.setattr(
        sys, "argv", [
            "clang-tools",
            "--uninstall", version,
            "--tool", tool_name,
            "--directory", install_dir,
        ]
    )
    main()
    # Verifies uninstall path was entered (printed the uninstall message)
    result = capsys.readouterr()
    assert "Uninstalling" in result.out


def test_main_install(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Test main() with --install flag."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", [
            "clang-tools",
            "--install", "12",
            "--tool", "clang-format",
            "--directory", str(tmp_path),
            "--no-progress-bar",
        ]
    )
    main()
    # Binary should be installed
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_invalid_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test main() with --install using a non-semver version."""
    monkeypatch.setattr(
        sys, "argv", [
            "clang-tools",
            "--install", "not-a-version",
            "--tool", "clang-format",
        ]
    )
    main()
    result = capsys.readouterr()
    assert "not a semantic" in result.out


def test_main_no_args(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test main() with no arguments shows help."""
    monkeypatch.setattr(sys, "argv", ["clang-tools"])
    main()
    result = capsys.readouterr()
    assert "Nothing to do" in result.out
