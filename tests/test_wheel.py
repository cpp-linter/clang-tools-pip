import sys
import pytest
from clang_tools.wheel import main, get_parser


def test_get_parser():
    """Test wheel's argument parser."""
    parser = get_parser()
    args = parser.parse_args(["--tool", "clang-format"])
    assert args.tool == "clang-format"
    assert args.version is None

    args = parser.parse_args(["--tool", "clang-tidy", "--version", "21.1.2"])
    assert args.tool == "clang-tidy"
    assert args.version == "21.1.2"


def test_get_parser_requires_tool():
    """Test wheel's argument parser requires --tool."""
    parser = get_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_main_success(monkeypatch):
    # Patch resolve_install to simulate success
    monkeypatch.setattr(
        "clang_tools.wheel.resolve_install",
        lambda tool, version: "/usr/bin/clang-format",
    )
    monkeypatch.setattr(
        sys, "argv", ["wheel.py", "--tool", "clang-format", "--version", "15.0.7"]
    )
    exit_code = main()
    assert exit_code == 0


def test_main_failure(monkeypatch):
    # Patch resolve_install to simulate failure
    monkeypatch.setattr("clang_tools.wheel.resolve_install", lambda tool, version: None)
    monkeypatch.setattr(
        sys, "argv", ["wheel.py", "--tool", "clang-format", "--version", "99.99.99"]
    )
    exit_code = main()
    assert exit_code == 1


def test_main_default_tool(monkeypatch):
    # Patch resolve_install to simulate success for default tool
    monkeypatch.setattr(
        "clang_tools.wheel.resolve_install",
        lambda tool, version: "/usr/bin/clang-format",
    )
    # The CLI requires --tool; simulate running with the default tool explicitly
    monkeypatch.setattr(sys, "argv", ["wheel.py", "--tool", "clang-format"])
    exit_code = main()
    assert exit_code == 0
