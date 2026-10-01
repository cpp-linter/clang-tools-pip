"""Tests related to installing a clang tool."""

import os
import subprocess
import sys
from pathlib import Path, PurePath
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from clang_tools import install_arch, install_os, suffix
from clang_tools.install import (
    clang_tools_binary_url,
    create_sym_link,
    install_clang_tools,
    install_dir_name,
    install_tool,
    is_installed,
    move_and_chmod_bin,
    uninstall_clang_tools,
    uninstall_tool,
)
from clang_tools.util import Version


@pytest.mark.parametrize("version", [str(v) for v in range(7, 17)])
@pytest.mark.parametrize(
    "tool_name",
    [
        "clang-format",
        "clang-tidy",
        "clang-query",
        "clang-apply-replacements",
        "clang-include-cleaner",
        "llvm-cov",
        "llvm-profdata",
        "llvm-symbolizer",
        "clang-scan-deps",
    ],
)
def test_clang_tools_binary_url(tool_name: str, version: str):
    """Test `clang_tools_binary_url()` parses a valid URL on the current OS."""
    url = clang_tools_binary_url(tool_name, version)
    if install_os == "macosx":
        if install_arch == "arm64":
            assert "_macos-arm64" in url
        else:
            assert "_macos-amd64" in url  # pragma: no cover
        return  # pragma: no cover — non-macos, tested separately


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


@pytest.mark.parametrize("version", ["18"])
def test_install_clang_include_cleaner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, version: str
):
    """Test install clang-include-cleaner binary (LLVM 18+)."""
    monkeypatch.chdir(tmp_path)
    tool_name = "clang-include-cleaner"
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
    2. indicates a failure when the requested version is out of the supported range
    """
    try:
        install_clang_tools(Version("0"), ["x"], ".", False, False)
    except ValueError as exc:
        if install_dir_name(".") not in os.environ.get("PATH", ""):  # pragma: no cover
            # this warning does not happen in an activated venv
            result = capsys.readouterr()
            assert "directory is not in your environment variable PATH" in result.out
        assert "is not available in static binary builds" in exc.args[0]


def test_install_tool_download_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that a failed download raises an OSError with a helpful message.

    Uses a non-URL string for the repo base to trigger a ValueError in urlopen,
    which download_file catches and returns None, causing install_tool to raise OSError.
    """
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    with pytest.raises(OSError, match="Failed to download"):
        install_tool("clang-format", "12", str(tmp_path), True)


def test_install_clang_tools_download_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test that a download failure inside install_clang_tools raises OSError.

    Covers the loop body (lines that iterate tools and call install_tool) by using a
    valid version with a broken repo URL, so the version check passes but the download
    fails.
    """
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    with pytest.raises(OSError, match="Failed to download"):
        install_clang_tools(Version("12"), ["clang-format"], str(tmp_path), False, True)


def test_is_installed_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test is_installed when the tool exists and has a matching major version."""
    tool_name = "clang-format"
    version = Version("12")
    exe_name = f"{tool_name}-{version.info[0]}{suffix}"
    fake_bin = tmp_path / exe_name
    fake_bin.write_bytes(b"fake binary")
    fake_bin.chmod(0o755)

    # Mock subprocess to return matching version output
    mock_result = Mock()
    mock_result.stdout = b"LLVM version 12.0.1\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
    monkeypatch.setattr("shutil.which", lambda x: str(fake_bin))

    result = is_installed(tool_name, version)
    assert result == fake_bin.resolve()


def test_is_installed_wrong_major_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test is_installed when the tool exists but has a different major version."""
    tool_name = "clang-format"
    version = Version("12")
    exe_name = f"{tool_name}-{version.info[0]}{suffix}"
    fake_bin = tmp_path / exe_name
    fake_bin.write_bytes(b"fake binary")
    fake_bin.chmod(0o755)

    # subprocess succeeds but returns a different major version
    mock_result = Mock()
    mock_result.stdout = b"LLVM version 14.0.0\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
    monkeypatch.setattr("shutil.which", lambda x: str(fake_bin))

    result = is_installed(tool_name, version)
    assert result is None


def test_is_installed_not_found_in_path(monkeypatch: pytest.MonkeyPatch):
    """Test is_installed when the tool runs but shutil.which can't find it."""
    tool_name = "clang-format"
    version = Version("15")

    mock_result = Mock()
    mock_result.stdout = b"LLVM version 15.0.0\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
    monkeypatch.setattr("shutil.which", lambda x: None)

    result = is_installed(tool_name, version)
    assert result is None


def test_install_tool_sha512_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test install_tool when existing binary has an invalid sha512 checksum.

    This forces a re-download."""
    monkeypatch.chdir(tmp_path)
    tool_name = "clang-format"
    version = "12"
    bin_name = f"{tool_name}-{version}{suffix}"

    # Pre-create the binary with invalid content
    existing_bin = tmp_path / bin_name
    existing_bin.write_bytes(b"corrupted binary data")

    # install_tool should detect invalid sha, uninstall, and re-download
    assert install_tool(tool_name, version, str(tmp_path), False)
    assert existing_bin.exists()


def test_move_and_chmod_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test move_and_chmod_bin directly."""
    monkeypatch.chdir(tmp_path)
    old_name = "downloaded-file"
    new_name = "clang-format-12"
    src_file = tmp_path / old_name
    src_file.write_bytes(b"binary content")

    install_dir = tmp_path / "bin"
    move_and_chmod_bin(old_name, new_name, str(install_dir))

    target = install_dir / new_name
    assert target.exists()
    assert not src_file.exists()  # moved, not copied
    assert os.access(target, os.X_OK)


def test_move_and_chmod_bin_create_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test move_and_chmod_bin creates install directory if it doesn't exist."""
    monkeypatch.chdir(tmp_path)
    old_name = "downloaded-file"
    new_name = "clang-format-12"
    src_file = tmp_path / old_name
    src_file.write_bytes(b"binary content")

    install_dir = tmp_path / "nested" / "bin"
    # directory does not exist yet
    assert not install_dir.exists()
    move_and_chmod_bin(old_name, new_name, str(install_dir))

    target = install_dir / new_name
    assert target.exists()
    assert os.access(target, os.X_OK)


def test_create_symlink_with_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test create_sym_link with an explicit target parameter."""
    monkeypatch.chdir(str(tmp_path))
    tool_name = "clang-tool"
    version = "1"

    # Create the target in a different location
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = target_dir / f"{tool_name}-{version}{suffix}"
    target.write_bytes(b"some binary data")

    # Create symlink pointing to the explicit target
    assert create_sym_link(tool_name, version, str(tmp_path), False, target=target)
    link = tmp_path / f"{tool_name}{suffix}"
    assert link.is_symlink()
    assert link.resolve() == target


def test_uninstall_tool_direct(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test uninstall_tool directly."""
    monkeypatch.chdir(str(tmp_path))
    tool_name = "clang-format"
    version = "12"
    bin_name = f"{tool_name}-{version}{suffix}"
    tool_path = tmp_path / bin_name
    tool_path.write_bytes(b"binary")

    assert tool_path.exists()
    uninstall_tool(tool_name, version, str(tmp_path))
    assert not tool_path.exists()


def test_uninstall_tool_with_dead_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test uninstall_tool cleans up a dead symlink."""
    monkeypatch.chdir(str(tmp_path))
    tool_name = "clang-format"
    version = "12"
    bin_name = f"{tool_name}-{version}{suffix}"

    # Create the actual tool binary
    tool_path = tmp_path / bin_name
    tool_path.write_bytes(b"binary")

    # Create a symlink
    link = tmp_path / f"{tool_name}{suffix}"
    link.symlink_to(tool_path)

    # Remove the actual binary to make the symlink dead
    tool_path.unlink()

    # Now the symlink exists but points to nothing
    assert link.is_symlink()
    assert not link.exists()

    # uninstall_tool should clean up the dead symlink
    uninstall_tool(tool_name, version, str(tmp_path))
    assert not link.exists()


def test_uninstall_tool_nonexistent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test uninstall_tool with a tool that doesn't exist (no-op)."""
    monkeypatch.chdir(str(tmp_path))
    # Should not raise any error
    uninstall_tool("clang-format", "99", str(tmp_path))


def test_install_dir_name_default():
    """Test install_dir_name returns proper default when no dir given."""
    result = install_dir_name("")
    # Result depends on OS; separate tests cover linux/macos branches.
    assert isinstance(result, str) and len(result) > 1


def test_install_clang_tools_path_not_in_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
):
    """Test install_clang_tools warns when install dir is not in PATH."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    with pytest.raises(OSError):
        install_clang_tools(Version("12"), ["clang-format"], str(tmp_path), False, True)

    result = capsys.readouterr()
    assert "directory is not in your environment variable PATH" in result.out


def test_clang_tools_binary_url_non_macos(monkeypatch: pytest.MonkeyPatch):
    """Test clang_tools_binary_url with a non-macOS platform string."""
    monkeypatch.setattr("clang_tools.install.install_os", "linux")
    monkeypatch.setattr("clang_tools.install.install_arch", "amd64")
    url = clang_tools_binary_url("clang-format", "12")
    assert "linux-amd64" in url


def test_install_dir_name_linux_default(monkeypatch: pytest.MonkeyPatch):
    """Test install_dir_name returns ~/.local/bin/ on Linux when no dir given."""
    monkeypatch.setattr("clang_tools.install.install_os", "linux")
    result = install_dir_name("")
    assert result == os.path.expanduser("~/.local/bin/")


def test_create_sym_link_nonexistent_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test create_sym_link creates the install directory if it doesn't exist."""
    monkeypatch.chdir(str(tmp_path))
    tool_name, version = "clang-tool", "1"
    # Create the target binary in tmp_path
    target = tmp_path / f"{tool_name}-{version}{suffix}"
    target.write_bytes(b"some binary data")

    # Use a nested subdir that does not exist yet
    new_dir = tmp_path / "new_install_dir"
    assert not new_dir.exists()

    assert create_sym_link(tool_name, version, str(new_dir), False, target=target)
    assert new_dir.exists()
    link = new_dir / f"{tool_name}{suffix}"
    assert link.is_symlink()


def test_clang_tools_binary_url_force_non_macos(monkeypatch: pytest.MonkeyPatch):
    """Hit the non-macos branch by monkeypatching install_os to 'linux'."""
    monkeypatch.setattr("clang_tools.install.install_os", "linux")
    monkeypatch.setattr("clang_tools.install.install_arch", "amd64")
    url = clang_tools_binary_url("clang-format", "18")
    assert "linux-amd64" in url


def test_install_dir_name_default_force_non_linux(monkeypatch: pytest.MonkeyPatch):
    """Hit the non-linux branch by monkeypatching install_os to 'darwin'."""
    monkeypatch.setattr("clang_tools.install.install_os", "darwin")
    result = install_dir_name("")
    import sys

    assert result == os.path.dirname(sys.executable)


@pytest.mark.parametrize(
    "os_name,arch,ext,platform",
    [
        ("linux", "amd64", "", "linux-amd64"),
        ("linux", "arm64", "", "linux-arm64"),
        ("macosx", "amd64", "", "macos-amd64"),
        ("macosx", "arm64", "", "macos-arm64"),
        ("windows", "amd64", ".exe", "windows-amd64"),
        ("windows", "arm64", ".exe", "windows-arm64"),
    ],
)
def test_clang_tools_binary_url_platforms(
    monkeypatch: pytest.MonkeyPatch, os_name: str, arch: str, ext: str, platform: str
):
    """Test the download URL of each supported platform."""
    monkeypatch.setattr("clang_tools.install.install_os", os_name)
    monkeypatch.setattr("clang_tools.install.install_arch", arch)
    monkeypatch.setattr("clang_tools.install.suffix", ext)
    monkeypatch.setattr("clang_tools.install.binary_repo", "https://example.com/r")
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    assert clang_tools_binary_url("clang-tidy", "18") == (
        "https://example.com/r/releases/download/2026.01.01-abc/"
        f"clang-tidy-18_{platform}{ext}"
    )


def test_binary_source_from_environment():
    """Test that CLANG_TOOLS_REPO and CLANG_TOOLS_TAG select the download source."""
    env = dict(
        os.environ,
        CLANG_TOOLS_REPO="https://example.com/mirror",
        CLANG_TOOLS_TAG="v1.2.3",
    )
    code = (
        "from clang_tools.install import clang_tools_binary_url;"
        "print(clang_tools_binary_url('clang-format', '18'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=str(PurePath(__file__).parent.parent),
    )
    assert result.stdout.startswith(
        "https://example.com/mirror/releases/download/v1.2.3/clang-format-18_"
    )


@pytest.mark.parametrize(
    "os_name,ext,command",
    [("linux", "", "clang-format-15"), ("windows", ".exe", "clang-format.exe")],
)
def test_is_installed_command(
    monkeypatch: pytest.MonkeyPatch, os_name: str, ext: str, command: str
):
    """Test the executable name that is_installed() looks for on each OS."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        raise FileNotFoundError(args[0])

    monkeypatch.setattr("clang_tools.install.install_os", os_name)
    monkeypatch.setattr("clang_tools.install.suffix", ext)
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert is_installed("clang-format", Version("15")) is None
    assert calls == [[command, "--version"]]


def test_is_installed_tool_fails(monkeypatch: pytest.MonkeyPatch):
    """Test is_installed when the found tool exits with an error."""

    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert is_installed("clang-format", Version("15")) is None


def test_install_tool_installs_published_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that the installed binary is the published one and is executable."""
    monkeypatch.chdir(tmp_path)
    install_dir = tmp_path / "bin"
    assert install_tool("clang-tidy", "17", str(install_dir), True)
    installed = install_dir / f"clang-tidy-17{suffix}"
    asset = clang_tools_binary_url("clang-tidy", "17").rsplit("/", 1)[-1]
    assert installed.read_bytes() == fake_release.published(asset)
    assert os.access(installed, os.X_OK)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bin"]


def test_install_tool_keeps_valid_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that a binary with a valid checksum is not downloaded again."""
    monkeypatch.chdir(tmp_path)
    assert install_tool("clang-tidy", "17", str(tmp_path), True)
    downloads = len(fake_release.requests)
    assert not install_tool("clang-tidy", "17", str(tmp_path), True)
    assert len(fake_release.requests) == downloads


def test_install_tool_rejects_corrupted_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that a download not matching the published checksum is an error."""
    monkeypatch.chdir(tmp_path)
    asset = clang_tools_binary_url("clang-format", "12").rsplit("/", 1)[-1]
    fake_release.serve(asset, b"not the published binary")
    with pytest.raises(ValueError, match="corrupted during download"):
        install_tool("clang-format", "12", str(tmp_path / "bin"), True)
    # nothing is left behind, in the install directory or in the CWD
    assert [p for p in tmp_path.rglob("*") if not p.is_dir()] == []


def test_install_tool_without_checksums(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that nothing is installed when the checksums cannot be fetched."""
    monkeypatch.chdir(tmp_path)
    fake_release.serve("SHA512SUMS", b"Not Found", status=404)
    with pytest.raises(HTTPError):
        install_tool("clang-format", "12", str(tmp_path / "bin"), True)
    assert [p for p in tmp_path.rglob("*") if not p.is_dir()] == []


def test_install_tool_ignores_files_in_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that the download does not write through a link in the CWD."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me", encoding="utf-8")
    url = clang_tools_binary_url("clang-format", "12")
    (cwd / PurePath(url).stem).symlink_to(victim)

    install_dir = tmp_path / "bin"
    assert install_tool("clang-format", "12", str(install_dir), True)
    assert victim.read_text(encoding="utf-8") == "keep me"
    installed = install_dir / f"clang-format-12{suffix}"
    assert not installed.is_symlink()
    assert installed.read_bytes() == fake_release.published(url.rsplit("/", 1)[-1])


def test_install_tool_unknown_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that a binary missing from the release is reported as a failure."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(OSError, match="Failed to download"):
        install_tool("clang-format", "99", str(tmp_path), True)


def test_move_and_chmod_bin_permission_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test the message when the install directory is not writable."""

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("shutil.move", deny)
    with pytest.raises(SystemExit, match="permission to install clang-format-12"):
        move_and_chmod_bin("downloaded", "clang-format-12", str(tmp_path))


def test_create_sym_link_overwrite_repoints_link(tmp_path: Path):
    """Test that only overwrite=True moves an existing link to a new version."""
    old = tmp_path / f"clang-tool-1{suffix}"
    old.write_bytes(b"1")
    new = tmp_path / f"clang-tool-2{suffix}"
    new.write_bytes(b"2")
    link = tmp_path / f"clang-tool{suffix}"

    assert create_sym_link("clang-tool", "1", str(tmp_path))
    assert not create_sym_link("clang-tool", "2", str(tmp_path))
    assert link.resolve() == old.resolve()
    assert create_sym_link("clang-tool", "2", str(tmp_path), overwrite=True)
    assert link.resolve() == new.resolve()


def test_create_sym_link_keeps_regular_file(tmp_path: Path, capsys):
    """Test that a file that is not a symlink is never replaced."""
    (tmp_path / f"clang-tool-1{suffix}").write_bytes(b"1")
    own = tmp_path / f"clang-tool{suffix}"
    own.write_bytes(b"installed by someone else")
    assert not create_sym_link("clang-tool", "1", str(tmp_path), overwrite=True)
    assert not own.is_symlink()
    assert own.read_bytes() == b"installed by someone else"
    assert "is not a symbolic link" in capsys.readouterr().out


@pytest.mark.parametrize("os_name", ["linux", "windows"])
def test_create_sym_link_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, os_name: str
):
    """Test the messages when the OS refuses to create the symlink."""
    (tmp_path / f"clang-tool-1{suffix}").write_bytes(b"1")

    def refuse(self, target, target_is_directory=False):
        raise OSError(1, "symlinks are not allowed")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    monkeypatch.setattr("clang_tools.install.install_os", os_name)
    assert not create_sym_link("clang-tool", "1", str(tmp_path))
    out = capsys.readouterr().out
    assert "Encountered an error when trying to create the symbolic link" in out
    assert "symlinks are not allowed" in out
    assert ("Enable developer mode" in out) is (os_name == "windows")


def test_uninstall_tool_keeps_live_symlink(tmp_path: Path):
    """Test that a link to another installed version is left alone."""
    v12 = tmp_path / f"clang-format-12{suffix}"
    v12.write_bytes(b"12")
    v13 = tmp_path / f"clang-format-13{suffix}"
    v13.write_bytes(b"13")
    link = tmp_path / f"clang-format{suffix}"
    link.symlink_to(v13)

    uninstall_tool("clang-format", "12", str(tmp_path))
    assert not v12.exists()
    assert link.is_symlink() and link.resolve() == v13.resolve()


def test_uninstall_tool_keeps_regular_file(tmp_path: Path):
    """Test that a file that is not a symlink is not removed."""
    own = tmp_path / f"clang-format{suffix}"
    own.write_bytes(b"installed by someone else")
    uninstall_tool("clang-format", "12", str(tmp_path))
    assert own.read_bytes() == b"installed by someone else"


def test_uninstall_clang_tools_relative_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    """Test uninstalling several tools from a directory relative to the CWD."""
    monkeypatch.chdir(tmp_path)
    install_dir = tmp_path / "bin"
    install_dir.mkdir()
    for tool in ("clang-format", "clang-tidy"):
        (install_dir / f"{tool}-12{suffix}").write_bytes(b"binary")
    uninstall_clang_tools(["clang-format", "clang-tidy"], "12", "bin")
    assert list(install_dir.iterdir()) == []
    assert "Uninstalling version 12 from" in capsys.readouterr().out


def test_install_dir_name_relative(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that an explicit directory is made absolute."""
    monkeypatch.chdir(tmp_path)
    assert install_dir_name("bin") == os.path.join(os.getcwd(), "bin")


def test_install_clang_tools_dir_in_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    """Test a full install into a directory that is in PATH."""
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.is_installed", lambda tool, ver: None)
    install_clang_tools(Version("12"), ["clang-format"], str(tmp_path), False, True)
    assert "not in your environment variable PATH" not in capsys.readouterr().out
    link = tmp_path / f"clang-format{suffix}"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / f"clang-format-12{suffix}").resolve()


def test_install_clang_tools_links_native_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that a matching binary found in PATH is linked, not downloaded."""
    native = tmp_path / "usr" / f"clang-format-12{suffix}"
    native.parent.mkdir()
    native.write_bytes(b"native binary")
    monkeypatch.setattr("clang_tools.install.is_installed", lambda tool, ver: native)
    install_dir = tmp_path / "bin"
    install_clang_tools(Version("12"), ["clang-format"], str(install_dir), False, True)
    assert fake_release.requests == []
    assert not (install_dir / f"clang-format-12{suffix}").exists()
    link = install_dir / f"clang-format{suffix}"
    assert link.is_symlink() and link.resolve() == native.resolve()


def test_install_clang_tools_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that installing another version moves the link only with overwrite."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.is_installed", lambda tool, ver: None)
    link = tmp_path / f"clang-format{suffix}"
    install_clang_tools(Version("12"), ["clang-format"], str(tmp_path), False, True)
    install_clang_tools(Version("13"), ["clang-format"], str(tmp_path), False, True)
    assert link.resolve() == (tmp_path / f"clang-format-12{suffix}").resolve()
    install_clang_tools(Version("13"), ["clang-format"], str(tmp_path), True, True)
    assert link.resolve() == (tmp_path / f"clang-format-13{suffix}").resolve()
