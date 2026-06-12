"""Tests that relate to the unified main.py CLI."""

from typing import Optional, List
from argparse import ArgumentParser
import sys
import pytest
from clang_tools import suffix
from clang_tools.main import get_parser, main, _is_version_like


class Args:
    """Pseudo namespace for testing argparse defaults (legacy top-level flags)."""

    command: Optional[str] = None
    directory: str = ""
    _legacy_install: Optional[str] = None
    overlay: bool = False
    overwrite: bool = False
    no_progress_bar: bool = False
    _legacy_uninstall: Optional[str] = None
    tool: List[str] = ["clang-format", "clang-tidy"]


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
#  Parser – new subcommands
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
#  Backward-compat legacy flags (still work)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arg_name", ["install", "uninstall"])
@pytest.mark.parametrize("arg_value", [str(v) for v in range(7, 17)])
def test_legacy_arg_parser(arg_name: str, arg_value: str, parser: ArgumentParser):
    """Test legacy --install/--uninstall flags still parse."""
    args = parser.parse_args([f"--{arg_name}={arg_value}"])
    assert getattr(args, f"_legacy_{arg_name}") == arg_value


@pytest.mark.parametrize("switch_name", ["overwrite", "no-progress-bar"])
def test_legacy_cli_switch(switch_name: str, parser: ArgumentParser):
    """Test legacy switches/flags."""
    args = parser.parse_args([f"--{switch_name}"])
    assert getattr(args, switch_name.replace("-", "_"))


def test_legacy_default_args(parser: ArgumentParser):
    """Test legacy default values."""
    args = parser.parse_args([])
    for name, value in args.__dict__.items():
        assert getattr(Args, name) == value


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


def test_main_legacy_uninstall(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
    """Legacy ``--uninstall`` flag still works."""
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
            "--uninstall",
            version,
            "--tool",
            tool_name,
            "--directory",
            install_dir,
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "Uninstalling" in result.out
    assert exit_code == 0


def test_main_legacy_install(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Legacy ``--install`` flag still works."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "--install",
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


def test_main_legacy_install_invalid_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Legacy ``--install`` with invalid version shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "--install",
            "not-a-version",
            "--tool",
            "clang-format",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "not a semantic" in result.err
    assert exit_code == 1


# ---- New ``install`` subcommand ---------------------------------------


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


def test_main_install_binary_requires_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--binary`` with a non-version target is an error."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "--binary",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "requires a version number" in result.err
    assert exit_code == 1


def test_main_install_binary_invalid_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--binary`` with a non-version target shows 'requires a version number'."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "not-a-version",
            "--binary",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "requires a version number" in result.err
    assert exit_code == 1


def test_main_install_binary_and_wheel_mutex(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--binary`` and ``--wheel`` together is an error."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "18",
            "--binary",
            "--wheel",
        ],
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


def test_main_install_wheel_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--wheel`` with a failing _wheel_install returns 1."""
    monkeypatch.setattr(
        "clang_tools.main._wheel_install", lambda tools, ver: 1
    )
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
        ["clang-tools", "install", "clang-format", "--wheel", "--version", "15.0.7"],
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
        [
            "clang-tools",
            "install",
            "18",
            "--wheel",
            "-t",
            "clang-tidy",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked == [(["clang-tidy"], "18")]


def test_main_install_auto_detect_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
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
    # Cause binary install to fail
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


def test_main_install_auto_detect_non_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
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
    result = capsys.readouterr()
    assert exit_code == 0
    assert tracked_install == [(["clang-tidy"], None)]


def test_main_install_auto_detect_out_of_range_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect goes straight to wheel for out-of-range versions."""
    # Version 99 is outside MIN_VERSION..MAX_VERSION, install_clang_tools
    # raises ValueError → caught → fallback to wheel
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
            "99",
            "--tool",
            "clang-format",
        ],
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


# ---- New ``uninstall`` subcommand -------------------------------------


def test_main_uninstall_subcommand(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
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


def test_main_legacy_install_and_uninstall(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
    """Legacy combined ``--install`` and ``--uninstall`` flags."""
    monkeypatch.chdir(tmp_path)
    version = "12"
    tool_name = "clang-format"
    # pre-create dummy to uninstall
    dummy_bin = tmp_path / f"{tool_name}-{version}{suffix}"
    dummy_bin.write_bytes(b"dummy")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "--uninstall",
            version,
            "--install",
            version,
            "--tool",
            tool_name,
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "Uninstalling" in result.out
