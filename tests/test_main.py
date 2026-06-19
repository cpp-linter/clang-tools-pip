"""Tests that relate to the unified main.py CLI."""

import sys
from argparse import ArgumentParser
import pytest
from clang_tools import suffix
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
    assert args.backend == "auto"
    assert args.explicit_version is None
    assert args.directory == ""
    assert args.overwrite is False
    assert args.no_progress_bar is False


def test_install_subcommand_multiple_tools(parser: ArgumentParser):
    args = parser.parse_args(["install", "clang-format", "clang-tidy"])
    assert args.tools == ["clang-format", "clang-tidy"]


def test_install_subcommand_backend_binary(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--version", "18", "--backend", "binary"]
    )
    assert args.backend == "binary"
    assert args.explicit_version == "18"


def test_install_subcommand_backend_wheel(parser: ArgumentParser):
    args = parser.parse_args(["install", "clang-format", "--backend", "wheel"])
    assert args.backend == "wheel"
    assert args.explicit_version is None


def test_install_subcommand_wheel_with_version(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--backend", "wheel", "--version", "15.0.7"]
    )
    assert args.backend == "wheel"
    assert args.tools == ["clang-format"]
    assert args.explicit_version == "15.0.7"


def test_install_subcommand_directory(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--version", "18", "-d", "/custom/path"]
    )
    assert args.directory == "/custom/path"


def test_install_subcommand_flags(parser: ArgumentParser):
    args = parser.parse_args(
        ["install", "clang-format", "--version", "18", "--overwrite", "--no-progress-bar"]
    )
    assert args.overwrite is True
    assert args.no_progress_bar is True


def test_uninstall_subcommand(parser: ArgumentParser):
    args = parser.parse_args(
        ["uninstall", "clang-format", "--version", "12"]
    )
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


def test_main_install_backend_binary(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """``clang-tools install clang-format --version 12 --backend binary``."""
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
            "--backend",
            "binary",
            "--directory",
            str(tmp_path),
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    bin_path = tmp_path / f"clang-format-12{suffix}"
    assert bin_path.exists()


def test_main_install_backend_binary_requires_version(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend binary`` without ``--version`` is an error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--backend", "binary"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "requires --version" in result.err
    assert exit_code == 1


def test_main_install_backend_binary_bad_semver(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend binary`` with a zeroed-out version (e.g. 0.0.0) shows the semantic-version error."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-tidy",
            "--version",
            "0.0.0",
            "--backend",
            "binary",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "not a semantic" in result.err
    assert exit_code == 1


def test_main_install_backend_wheel_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--backend wheel`` with a tool name succeeds via mocked _wheel_install."""
    monkeypatch.setattr(
        "clang_tools.main._wheel_install",
        lambda tools, ver: 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--backend", "wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert result.err == ""


def test_main_install_backend_wheel_unsupported_tool(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend wheel`` with a binary-only tool name shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-query", "--backend", "wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "is not available as a wheel" in result.err
    assert exit_code == 1


def test_main_install_backend_wheel_include_cleaner(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend wheel`` with clang-include-cleaner succeeds."""
    monkeypatch.setattr(
        "clang_tools.main._wheel_install",
        lambda tools, ver: 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-include-cleaner", "--backend", "wheel"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert result.err == ""


def test_main_install_backend_wheel_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """``--backend wheel`` with a failing _wheel_install returns 1."""
    monkeypatch.setattr("clang_tools.main._wheel_install", lambda tools, ver: 1)
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-format", "--backend", "wheel"],
    )
    exit_code = main()
    assert exit_code == 1


def test_main_install_backend_wheel_version_arg(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend wheel`` with ``--version`` passes version to _wheel_install."""
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
            "--backend",
            "wheel",
            "--version",
            "15.0.7",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked_version == [(["clang-format"], "15.0.7")]


def test_main_install_auto_no_version(monkeypatch: pytest.MonkeyPatch, capsys):
    """Auto-detect without --version goes to wheel install."""
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


def test_main_install_auto_new_wheel_tools(monkeypatch: pytest.MonkeyPatch, capsys):
    """Auto-detect treats clang-include-cleaner / clang-apply-replacements as wheel."""
    tracked = []

    def mock_wheel(tools, version):
        tracked.append((tools, version))
        return 0

    monkeypatch.setattr("clang_tools.main._wheel_install", mock_wheel)

    monkeypatch.setattr(
        sys, "argv", ["clang-tools", "install", "clang-include-cleaner"]
    )
    assert main() == 0

    monkeypatch.setattr(
        sys, "argv", ["clang-tools", "install", "clang-apply-replacements"]
    )
    assert main() == 0

    assert tracked == [
        (["clang-include-cleaner"], None),
        (["clang-apply-replacements"], None),
    ]


def test_main_install_auto_with_version_success(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path
):
    """Auto-detect: tool name + --version tries binary first (succeeds)."""
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


def test_main_install_auto_with_version_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path
):
    """Auto-detect: tool name + --version falls back to wheel when binary fails."""
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
            "clang-tidy",
            "--version",
            "12",
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 0
    assert "falling back to wheel" in result.err


def test_main_install_auto_with_version_out_of_range(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect: tool + --version with out-of-range version falls back to wheel."""
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
            "clang-format",
            "--version",
            "99",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked == [(["clang-format"], "99")]


def test_main_install_auto_with_version_bad_semver(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """Auto-detect: tool + --version with 0.0.0 falls back to wheel."""
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
            "clang-tidy",
            "--version",
            "0.0.0",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    assert tracked == [(["clang-tidy"], "0.0.0")]


def test_main_install_auto_unsupported_tool(monkeypatch: pytest.MonkeyPatch, capsys):
    """Auto-detect with a binary-only tool name shows error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tools", "install", "clang-query"],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert "Unknown tool" in result.err
    assert exit_code == 1


def test_main_install_auto_multiple_tools(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path
):
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


# ---------------------------------------------------------------------------
#  _wheel_install helper tests
# ---------------------------------------------------------------------------


def test_wheel_install_none_none_fallback(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install when resolve_wheel_install returns (None, None) —
    a defensive fallback branch."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "clang_tools.wheel_install.resolve_wheel_install",
        lambda t, v: (None, None),
    )
    assert _wheel_install(["clang-format"], "18") == 1
    assert "Failed to install clang-format" in capsys.readouterr().err


def test_wheel_install_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install directly with a mocked resolve_wheel_install (success)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "clang_tools.wheel_install.resolve_wheel_install",
        lambda t, v: (f"/fake/{t}", None),
    )
    assert _wheel_install(["clang-format"], "18") == 0
    assert "installed at:" in capsys.readouterr().out


def test_wheel_install_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install directly with a failing resolve_wheel_install."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "clang_tools.wheel_install.resolve_wheel_install",
        lambda t, v: (None, "ERROR: resolve failed"),
    )
    assert _wheel_install(["clang-tidy"], "21") == 1
    assert "ERROR: resolve failed" in capsys.readouterr().err


def test_wheel_install_latest_success(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with version=None ("latest version" path, success)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "clang_tools.wheel_install.resolve_wheel_install",
        lambda t, v: (f"/fake/{t}", None),
    )
    assert _wheel_install(["clang-format"], None) == 0
    result = capsys.readouterr()
    assert "latest version" in result.out
    assert "installed at:" in result.out


def test_wheel_install_latest_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with version=None (version-resolution error, failure)."""
    from clang_tools.main import _wheel_install

    monkeypatch.setattr(
        "clang_tools.wheel_install.resolve_wheel_install",
        lambda t, v: (None, "TEST_ERROR: version not found"),
    )
    assert _wheel_install(["clang-tidy"], None) == 1
    result = capsys.readouterr()
    assert "TEST_ERROR: version not found" in result.err


def test_wheel_install_multiple_tools_mixed(monkeypatch: pytest.MonkeyPatch, capsys):
    """Test _wheel_install with multiple tools where one fails and one succeeds."""
    from clang_tools.main import _wheel_install

    def mock_resolve(tool, version):
        if tool == "clang-tidy":
            return None, "TEST_ERROR: failed"
        return f"/fake/{tool}", None

    monkeypatch.setattr("clang_tools.wheel_install.resolve_wheel_install", mock_resolve)
    assert _wheel_install(["clang-format", "clang-tidy"], "18") == 1
    result = capsys.readouterr()
    assert "installed at: /fake/clang-format" in result.out
    assert "TEST_ERROR: failed" in result.err


# ---------------------------------------------------------------------------
#  --backend binary fallback tests
# ---------------------------------------------------------------------------


def test_main_install_backend_binary_download_error(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    """``--backend binary`` that fails reports the error and returns 1."""
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clang-tools",
            "install",
            "clang-format",
            "--version",
            "12",
            "--backend",
            "binary",
            "--no-progress-bar",
        ],
    )
    exit_code = main()
    result = capsys.readouterr()
    assert exit_code == 1
    assert "Binary install failed" in result.err
