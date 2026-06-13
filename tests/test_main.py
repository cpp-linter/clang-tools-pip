"""Tests that relate to the unified main.py CLI."""

import sys
from argparse import ArgumentParser
import pytest
from clang_tools import suffix
from clang_tools.main import get_parser, main, _is_version_like


# ---------------------------------------------------------------------------
#  _is_version_like helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target,expected",
    [
        ("18", True),
        ("18.1", True),
        ("18.1.0", True),
        ("clang-format", False),
        ("clang-tidy", False),
        ("abc", False),
    ],
)
def test_is_version_like(target: str, expected: bool):
    assert _is_version_like(target) is expected


# ---------------------------------------------------------------------------
#  Parser – install subcommand
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> ArgumentParser:
    return get_parser()


def test_install_subcommand_defaults(parser: ArgumentParser):
    """Default values for the ``install`` subcommand."""
    args = parser.parse_args(["install", "18"])
    assert args.command == "install"
    assert args.target == "18"
    assert args.binary is False
    assert args.wheel is False
    assert args.tool == ["clang-format", "clang-tidy"]
    assert args.directory == ""
    assert args.overwrite is False
    assert args.no_progress_bar is False


def test_install_subcommand_binary(parser: ArgumentParser):
    args = parser.parse_args(["install", "18", "--binary"])
    assert args.binary is True
    assert args.wheel is False


def test_install_subcommand_wheel(parser: ArgumentParser):
    args = parser.parse_args(["install", "clang-format", "--wheel"])
    assert args.wheel is True
    assert args.binary is False


def test_install_subcommand_wheel_with_version(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--wheel", "--version", "15.0.7"]
    )
    assert args.wheel is True
    assert args.target == "clang-format"
    assert args.explicit_version == "15.0.7"


def test_install_subcommand_custom_tools(parser: ArgumentParser):
    args = parser.parse_args(["install", "18", "-t", "clang-tidy"])
    assert args.tool == ["clang-tidy"]


def test_install_subcommand_directory(parser: ArgumentParser):
    args = parser.parse_args(["install", "18", "-d", "/custom/path"])
    assert args.directory == "/custom/path"


def test_install_subcommand_flags(parser: ArgumentParser):
    args = parser.parse_args(["install", "18", "--overwrite", "--no-progress-bar"])
    assert args.overwrite is True
    assert args.no_progress_bar is True


def test_uninstall_subcommand(parser: ArgumentParser):
    args = parser.parse_args(["uninstall", "12", "-t", "clang-format"])
    assert args.command == "uninstall"
    assert args.version == "12"
    assert args.tool == ["clang-format"]


def test_uninstall_subcommand_defaults(parser: ArgumentParser):
    args = parser.parse_args(["uninstall", "12"])
    assert args.tool == ["clang-format", "clang-tidy"]
    assert args.directory == ""


# ---------------------------------------------------------------------------
#  Integration / functional tests
# ---------------------------------------------------------------------------


def test_main_no_args(monkeypatch: pytest.MonkeyPatch, capsys):
    """``clang-tools`` with no args prints help."""
    monkeypatch.setattr(sys, "argv", ["clang-tools"])
    exit_code = main()
    result = capsys.readouterr()
    assert "Nothing to do" in result.err
    assert exit_code == 0


# ---- ``install`` subcommand -------------------------------------------


def test_main_install_binary(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """``clang-tools install 12 --binary`` installs binary."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "12",
            "--binary",
            "--tool",
            "clang-format",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_binary_requires_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--binary`` with a non-version target is an error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--binary"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "requires a version number" in result.err
    assert exit_code == 1


def test_main_install_binary_invalid_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--binary`` with a non-version target shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "not-a-version", "--binary"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "requires a version number" in result.err
    assert exit_code == 1


def test_main_install_binary_and_wheel_mutex(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--binary`` and ``--wheel`` together is an error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "18", "--binary", "--wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "mutually exclusive" in result.err
    assert exit_code == 1


def test_main_install_wheel_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--wheel`` with a tool name succeeds via mocked _wheel_install."""
    monkeypatch.setattr(
        "clang_tools.main._wheel_install",
        lambda tools, ver: 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert result.err == ""


def test_main_install_wheel_unsupported_tool(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--wheel`` with a binary-only tool name shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-query", "--wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "is not available as a wheel" in result.err
    assert exit_code == 1


def test_main_install_wheel_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--wheel`` with a failing _wheel_install returns 1."""
    monkeypatch.setattr("clang_tools.main._wheel_install", lambda tools, ver: 1)
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--wheel"],
    )
    exit_code = main()
    assert exit_code == 1


def test_main_install_wheel_version_arg(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--wheel`` with ``--version`` passes version to _wheel_install."""
    tracked_version = []

    def mock_wheel(tools, version):
        tracked_version.append((tools, version))
        return 0

    monkeypatch.setattr("clang_tools.main._wheel_install", mock_wheel)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "--wheel",
            "--version",
            "15.0.7",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked_version == [(["clang-format"], "15.0.7")]


def test_main_install_wheel_with_version_as_target(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``clang-tools install 18 --wheel`` uses version as target, tool from -t."""
    tracked: list = []

    def mock_wheel(tools, version):
        tracked.append((tools, version))
        return 0

    monkeypatch.setattr("clang_tools.main._wheel_install", mock_wheel)
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "18", "--wheel", "-t", "clang-tidy"],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked == [(["clang-tidy"], "18")]


def test_main_install_auto_detect_binary(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Auto-detect installs binary for version in supported range."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "12",
            "--tool",
            "clang-format",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_auto_detect_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
    """Auto-detect falls back to wheel when binary fails."""
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    monkeypatch.setattr(
        "clang_tools.main._wheel_install",
        lambda tools, ver: 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "12",
            "--tool",
            "clang-format",
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "falling back to wheel" in result.err


def test_main_install_auto_detect_non_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """Auto-detect treats non-version target as tool name (wheel install)."""
    tracked_install: list = []

    def mock_wheel(tools, version):
        tracked_install.append((tools, version))
        return 0

    monkeypatch.setattr("clang_tools.main._wheel_install", mock_wheel)
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-tidy"],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked_install == [(["clang-tidy"], None)]


def test_main_install_auto_detect_out_of_range_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect falls back to wheel for out-of-range versions."""
    monkeypatch.setattr(
        "clang_tools.main._wheel_install",
        lambda tools, ver: 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "99", "--tool", "clang-format"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "falling back to wheel" in result.err


def test_main_install_auto_detect_invalid_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect with a non-version, non-tool target shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "abc.def"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "Unknown target" in result.err
    assert exit_code == 1


# ---- ``uninstall`` subcommand -----------------------------------------


def test_wheel_install_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install directly with a mocked resolve_install (success)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "cpp_linter_hooks.util.resolve_install", lambda t, v: f"/fake/{t}"
    )
    assert _wheel_install(["clang-format"], "18") == 0
    assert "installed at:" in capsys.readouterr().out


def test_wheel_install_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install directly with a failing resolve_install."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr("cpp_linter_hooks.util.resolve_install", lambda t, v: None)
    assert _wheel_install(["clang-tidy"], "21") == 1
    assert "Failed to install" in capsys.readouterr().err


def test_main_install_binary_bad_semver(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--binary`` with a version-like but zeroed-out version (e.g. 0.0.0)."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "0.0.0", "--binary"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 1
    assert "not a semantic" in result.err


def test_main_uninstall_subcommand(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys):
    """``clang-tools uninstall 12`` removes installed tools."""
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
            version,
            "--tool",
            tool_name,
            "--directory",
            install_dir,
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "Uninstalling" in result.out
    assert not dummy_bin.exists()


# ---------------------------------------------------------------------------
#  Additional _wheel_install coverage (version=None, multi-tool mix)
# ---------------------------------------------------------------------------


def test_wheel_install_latest_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with version=None ("latest version" path, success)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "cpp_linter_hooks.util.resolve_install", lambda t, v: f"/fake/{t}"
    )
    assert _wheel_install(["clang-format"], None) == 0
    result = capsys.readouterr()
    assert "latest version" in result.out
    assert "installed at:" in result.out


def test_wheel_install_latest_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with version=None ("latest version" path, failure)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr("cpp_linter_hooks.util.resolve_install", lambda t, v: None)
    assert _wheel_install(["clang-tidy"], None) == 1
    result = capsys.readouterr()
    assert "latest version" in result.err
    assert "Failed to install" in result.err


def test_wheel_install_multiple_tools_mixed(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with multiple tools where one fails and one succeeds."""
    from clang_tools.main import _wheel_install

    def mock_resolve(tool, version):
        if tool == "clang-tidy":
            return None  # fails
        return f"/fake/{tool}"  # succeeds

    monkeypatch.setattr("cpp_linter_hooks.util.resolve_install", mock_resolve)
    assert _wheel_install(["clang-format", "clang-tidy"], "18") == 1
    result = capsys.readouterr()
    assert "installed at: /fake/clang-format" in result.out
    assert "Failed to install clang-tidy" in result.err


# ---------------------------------------------------------------------------
#  Additional _handle_auto_detect coverage (bad semver path)
# ---------------------------------------------------------------------------


def test_main_install_auto_detect_bad_semver(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect with a version that parses to (0,0,0) shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "0.0.0"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 1
    assert "not a semantic" in result.err
