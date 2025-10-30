import sys
from clang_tools.wheel import main


def test_main_success(monkeypatch):
    # Patch _resolve_install to simulate success
    monkeypatch.setattr(
        "clang_tools.wheel._resolve_install",
        lambda tool, version: "/usr/bin/clang-format",
    )
    monkeypatch.setattr(
        sys, "argv", ["util.py", "--tool", "clang-format", "--version", "15.0.7"]
    )
    exit_code = main()
    assert exit_code == 0


def test_main_failure(monkeypatch):
    # Patch _resolve_install to simulate failure
    monkeypatch.setattr(
        "clang_tools.wheel._resolve_install", lambda tool, version: None
    )
    monkeypatch.setattr(
        sys, "argv", ["util.py", "--tool", "clang-format", "--version", "99.99.99"]
    )
    exit_code = main()
    assert exit_code == 1


def test_main_default_tool(monkeypatch):
    # Patch _resolve_install to simulate success for default tool
    monkeypatch.setattr(
        "clang_tools.wheel._resolve_install",
        lambda tool, version: "/usr/bin/clang-format",
    )
    monkeypatch.setattr(sys, "argv", ["util.py"])
    exit_code = main()
    assert exit_code == 0
