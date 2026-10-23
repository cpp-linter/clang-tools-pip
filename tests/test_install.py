"""Tests related to installing a clang tool."""

import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path, PurePath
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from conftest import headers_dir_name, make_tar

from clang_tools import MAX_VERSION, MIN_VERSION, install_arch, install_os, suffix
from clang_tools.install import (
    available_versions,
    binary_file_name,
    clang_tools_binary_url,
    create_install_dir,
    create_sym_link,
    data_dir,
    default_install_dir,
    extract_headers,
    find_binary,
    install_clang_tools,
    install_dir_name,
    install_tool,
    is_in_path,
    is_installed,
    is_managed,
    link_binary,
    platform_name,
    uninstall_clang_tools,
    uninstall_tool,
)
from clang_tools.util import PyPIFallback, Version


@pytest.mark.parametrize(
    "version", [str(v) for v in range(MIN_VERSION, MAX_VERSION + 1)]
)
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
    uninstall_clang_tools([tool_name], version, str(tmp_path))
    assert f"{tool_name}-{version}{suffix}" not in [
        fd.name for fd in tmp_path.iterdir()
    ]


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
    uninstall_clang_tools([tool_name], version, str(tmp_path))
    assert f"{tool_name}-{version}{suffix}" not in [
        fd.name for fd in tmp_path.iterdir()
    ]


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
    except PyPIFallback as exc:
        if not is_in_path(install_dir_name(".")):  # pragma: no cover
            # this warning does not happen in an activated venv
            result = capsys.readouterr()
            assert "directory is not in your environment variable PATH" in result.out
        assert "is not available in static binary builds" in exc.args[0]


def test_install_tool_download_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that a failed download triggers the PyPI fallback with a helpful message.

    Uses a non-URL string for the release download to trigger a ValueError in
    urlopen, which download_file raises as `PyPIFallback`.
    """
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    monkeypatch.setattr("clang_tools.install.get_sha_checksum", lambda url: "0" * 128)
    with pytest.raises(PyPIFallback, match="Failed to download") as exc_info:
        install_tool("clang-format", "12", str(tmp_path), True)
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_install_clang_tools_download_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test that a download failure inside install_clang_tools triggers the fallback.

    Covers the loop body (lines that iterate tools and call install_tool) by using a
    valid version with a broken repo URL, so the version check passes but the download
    fails.
    """
    monkeypatch.setattr("clang_tools.install.binary_repo", "not-a-valid-url")
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    monkeypatch.setattr("clang_tools.install.get_sha_checksum", lambda url: "0" * 128)
    with pytest.raises(PyPIFallback, match="Failed to download"):
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

    # install_tool replaces the file with a link to the verified binary
    assert install_tool(tool_name, version, str(tmp_path), False)
    assert existing_bin.is_symlink()
    assert existing_bin.read_bytes() != b"corrupted binary data"


def test_link_binary(tmp_path: Path, capsys):
    """Test that the install directory gets a link to the stored binary."""
    stored = tmp_path / "data" / "bin" / "clang-format-12"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"binary content")
    destination = tmp_path / "clang-format-12"
    destination.write_bytes(b"an older copy")

    link_binary(stored, destination)
    assert destination.is_symlink()
    assert destination.resolve() == stored.resolve()
    assert "Installing clang-format-12 to" in capsys.readouterr().out
    link_binary(stored, destination)  # already linked: nothing to do
    assert capsys.readouterr().out == ""


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
    monkeypatch.setattr("clang_tools.install.index_url", "not-a-valid-url")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    with pytest.raises(PyPIFallback):
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
    assert result == os.path.realpath(os.path.expanduser("~/.local/bin"))


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
    assert result == os.path.realpath(os.path.dirname(sys.executable))


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
    install_dir.mkdir()
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
    with pytest.raises(PyPIFallback, match="corrupted during download"):
        install_tool("clang-format", "12", str(tmp_path / "bin"), True)
    # nothing is left behind, in the install directory or in the CWD
    assert [p for p in tmp_path.rglob("*") if not p.is_dir()] == []


def test_install_tool_without_checksums(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that nothing is installed when the checksums cannot be fetched."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    fake_release.serve("SHA512SUMS", b"Not Found", status=404)
    with pytest.raises(PyPIFallback, match="SHA512SUMS") as exc_info:
        install_tool("clang-format", "12", str(tmp_path / "bin"), True)
    assert isinstance(exc_info.value.__cause__, HTTPError)
    assert [p for p in tmp_path.rglob("*") if not p.is_dir()] == []


def test_install_tool_ignores_files_in_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
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
    install_dir.mkdir()
    assert install_tool("clang-format", "12", str(install_dir), True)
    assert victim.read_text(encoding="utf-8") == "keep me"
    installed = install_dir / f"clang-format-12{suffix}"
    assert installed.resolve().is_relative_to(data_root)
    assert installed.read_bytes() == fake_release.published(url.rsplit("/", 1)[-1])


def test_install_tool_unknown_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that a binary missing from the release is reported as a failure."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    monkeypatch.setattr("clang_tools.install.get_sha_checksum", lambda url: "0" * 128)
    with pytest.raises(PyPIFallback, match="Failed to download"):
        install_tool("clang-format", "99", str(tmp_path), True)


def test_install_tool_version_not_in_index(tmp_path: Path):
    """Test that a version missing from the index is reported with the choices."""
    with pytest.raises(PyPIFallback, match="Available versions: 12, 13,"):
        install_tool("clang-format", "99", str(tmp_path), True)


def test_find_binary_from_index(monkeypatch: pytest.MonkeyPatch, fake_release):
    """Test that the URL and checksum come from the index, for any 18.x.y."""
    monkeypatch.setattr("clang_tools.install.install_os", "linux")
    monkeypatch.setattr("clang_tools.install.install_arch", "arm64")
    binary = find_binary("clang-tidy", "18.1.8")
    assert binary.url.endswith(
        "/releases/download/llvm-18.1.0/clang-tidy-18_linux-arm64"
    )
    assert binary.tag == "llvm-18.1.0"
    assert binary.headers is not None
    assert binary.headers[0].endswith("/llvm-18.1.0/clang-resource-headers-18.tar.gz")
    assert (
        binary.sha512
        == fake_release._index()["versions"]["18"]["tools"]["clang-tidy"][
            "linux-arm64"
        ]["sha512"]
    )
    assert fake_release.downloads() == ["index.json"]


def test_find_binary_tool_not_in_version(fake_release):
    """Test that a tool missing from a version (e.g. too old) is an error."""
    del fake_release._index()["versions"]["12"]["tools"]["clang-include-cleaner"]
    with pytest.raises(PyPIFallback, match="clang-include-cleaner 12 is not available"):
        find_binary("clang-include-cleaner", "12")


def test_install_tool_uses_index_checksum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test that only the index and the binary are downloaded (no SHA512SUMS)."""
    monkeypatch.chdir(tmp_path)
    assert install_tool("clang-format", "21", str(tmp_path), True)
    asset = clang_tools_binary_url("clang-format", "21").rsplit("/", 1)[-1]
    assert fake_release.downloads() == ["index.json", asset]


def test_available_versions(monkeypatch: pytest.MonkeyPatch, fake_release):
    """Test that the versions come from the index unless a tag is pinned."""
    del fake_release._index()["versions"]["12"]
    assert available_versions() == list(range(13, MAX_VERSION + 1))
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    assert available_versions() == list(range(MIN_VERSION, MAX_VERSION + 1))


def test_index_url_from_environment():
    """Test that CLANG_TOOLS_INDEX_URL selects the index."""
    env = dict(os.environ, CLANG_TOOLS_INDEX_URL="https://example.com/index.json")
    env.pop("CLANG_TOOLS_TAG", None)
    code = "from clang_tools import index_url, binary_tag; print(index_url, binary_tag)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=str(PurePath(__file__).parent.parent),
    )
    assert result.stdout.split() == ["https://example.com/index.json"]


def test_link_binary_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test the message when the install directory is not writable."""

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "symlink_to", deny)
    monkeypatch.setattr("shutil.copy2", deny)
    with pytest.raises(SystemExit, match="permission to install clang-format-12"):
        link_binary(tmp_path / "stored", tmp_path / "clang-format-12")


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


def test_create_sym_link_replaces_dangling_link(tmp_path: Path):
    """Test that overwrite=True replaces a link whose target was removed."""
    target = tmp_path / f"clang-tool-1{suffix}"
    target.write_bytes(b"1")
    link = tmp_path / f"clang-tool{suffix}"
    link.symlink_to(tmp_path / f"clang-tool-0{suffix}")  # does not exist

    assert create_sym_link("clang-tool", "1", str(tmp_path), overwrite=True)
    assert link.resolve() == target.resolve()


def test_create_sym_link_keeps_dangling_link(tmp_path: Path, capsys):
    """Test that a dangling link is only replaced with overwrite=True."""
    (tmp_path / f"clang-tool-1{suffix}").write_bytes(b"1")
    link = tmp_path / f"clang-tool{suffix}"
    link.symlink_to(tmp_path / f"clang-tool-0{suffix}")  # does not exist

    assert not create_sym_link("clang-tool", "1", str(tmp_path))
    assert link.is_symlink() and not link.exists()  # still the dangling link
    assert "Use '-f' to overwrite" in capsys.readouterr().out


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
    assert install_dir_name("bin") == os.path.realpath(os.path.join(os.getcwd(), "bin"))


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
    """Test that a matching binary found in PATH is linked, not downloaded.

    The index is not fetched either, so this works offline.
    """
    native = tmp_path / "usr" / f"clang-format-12{suffix}"
    native.parent.mkdir()
    native.write_bytes(b"native binary")
    monkeypatch.setattr("clang_tools.install.is_installed", lambda tool, ver: native)
    install_dir = tmp_path / "bin"
    install_clang_tools(Version("12"), ["clang-format"], str(install_dir), False, True)
    assert fake_release.downloads() == []  # neither the index nor a binary
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


@pytest.mark.parametrize(
    "tool_name,version",
    [("../clang-format", "18"), ("clang-format", "18/../../x"), ("..", ""), ("", "18")],
)
def test_binary_file_name_rejects_paths(tool_name: str, version: str, tmp_path: Path):
    """Test that a tool name or version cannot point outside the install directory."""
    with pytest.raises(ValueError, match="Invalid tool name or version"):
        binary_file_name(tool_name, version)
    with pytest.raises(PyPIFallback, match="Invalid tool name or version"):
        install_tool(tool_name, version, str(tmp_path), True)
    with pytest.raises(ValueError, match="Invalid tool name or version"):
        uninstall_tool(tool_name, version, str(tmp_path))


def test_binary_file_name():
    """Test the file name of an installed binary."""
    assert binary_file_name("clang-format", "18.1.8") == f"clang-format-18.1.8{suffix}"


def test_install_dir_name_resolves_symlink(tmp_path: Path):
    """Test that a directory reached through a symlink is used in resolved form."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert install_dir_name(str(link)) == os.path.realpath(real)


def test_install_dir_name_not_a_directory(tmp_path: Path, capsys):
    """Test that a path to a file falls back to the default directory."""
    not_a_dir = tmp_path / "file"
    not_a_dir.write_bytes(b"not a directory")
    assert install_dir_name(str(not_a_dir)) == default_install_dir()
    message = f"{os.path.realpath(not_a_dir)} is not a directory"
    assert message in capsys.readouterr().err
    assert not_a_dir.read_bytes() == b"not a directory"


def test_create_install_dir(tmp_path: Path):
    """Test that a missing install directory is created."""
    install_dir = tmp_path / "bin"
    create_install_dir(str(install_dir))
    assert install_dir.is_dir()
    create_install_dir(str(install_dir))  # already exists
    assert install_dir.is_dir()


def test_create_install_dir_missing_parent(tmp_path: Path):
    """Test that the parents of a given directory are not created."""
    install_dir = tmp_path / "typo" / "bin"
    with pytest.raises(SystemExit, match="because .*typo does not exist"):
        create_install_dir(str(install_dir))
    assert not (tmp_path / "typo").exists()


def test_create_install_dir_default_parents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Test that the parents of the default directory (``~/.local``) are created."""
    default = str(tmp_path / "home" / ".local" / "bin")
    monkeypatch.setattr("clang_tools.install.default_install_dir", lambda: default)
    create_install_dir(default)
    assert Path(default).is_dir()


def test_create_install_dir_is_a_file(tmp_path: Path):
    """Test the message when the install directory can't be created."""
    not_a_dir = tmp_path / "file"
    not_a_dir.write_bytes(b"not a directory")
    with pytest.raises(SystemExit, match="Can't create the install directory"):
        create_install_dir(str(not_a_dir))
    assert not_a_dir.read_bytes() == b"not a directory"


def test_install_clang_tools_missing_parent(tmp_path: Path, fake_release):
    """Test that nothing is downloaded when the install directory can't be made."""
    install_dir = tmp_path / "typo" / "bin"
    with pytest.raises(SystemExit, match="does not exist"):
        install_clang_tools(
            Version("12"), ["clang-format"], str(install_dir), False, True
        )
    assert fake_release.downloads() == []
    assert not (tmp_path / "typo").exists()


def test_is_in_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that PATH entries are compared as resolved directories."""
    real = tmp_path / "bin"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    resolved = os.path.realpath(real)

    monkeypatch.setenv("PATH", os.pathsep.join(["", str(link)]))
    assert is_in_path(resolved)
    # an entry that only starts with the same characters is another directory
    monkeypatch.setenv("PATH", str(tmp_path / "bin2"))
    assert not is_in_path(resolved)
    monkeypatch.delenv("PATH")
    assert not is_in_path(resolved)


# ---------------------------------------------------------------------------
#  The data directory and the clang resource headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", [15, 21])
def test_install_tool_installs_headers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_release,
    data_root: Path,
    version: int,
):
    """Test that clang-tidy is linked to a binary next to its resource headers."""
    monkeypatch.chdir(tmp_path)
    assert install_tool("clang-tidy", str(version), str(tmp_path), True)
    prefix = data_root / f"llvm-{version}.1.0"
    stored = prefix / "bin" / f"clang-tidy-{version}{suffix}"
    installed = tmp_path / f"clang-tidy-{version}{suffix}"
    assert installed.resolve() == stored.resolve()
    assert os.access(stored, os.X_OK)
    # where clang looks for them: <real path of the binary>/../lib/clang/<version>
    include = stored.parent.parent / "lib" / "clang" / headers_dir_name(version)
    assert (include / "include" / "stddef.h").is_file()
    assert sorted(p.name for p in prefix.iterdir()) == ["bin", "lib"]
    assert fake_release.downloads() == [
        "index.json",
        f"clang-tidy-{version}_{platform_name()}{suffix}",
        f"clang-resource-headers-{version}.tar.gz",
    ]

    # another install directory reuses the binary and the headers
    other = tmp_path / "other"
    other.mkdir()
    assert not install_tool("clang-tidy", str(version), str(other), True)
    assert fake_release.downloads()[3:] == []
    assert (other / f"clang-tidy-{version}{suffix}").resolve() == stored.resolve()


def test_install_tool_without_headers_for_clang_format(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
):
    """Test that tools that don't parse code don't download the headers."""
    monkeypatch.chdir(tmp_path)
    assert install_tool("clang-format", "21", str(tmp_path), True)
    assert not (data_root / "llvm-21.1.0" / "lib").exists()


def test_install_tool_redownloads_corrupted_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
):
    """Test that a stored binary that doesn't match its checksum is replaced."""
    monkeypatch.chdir(tmp_path)
    stored = data_root / "llvm-12.1.0" / "bin" / f"clang-format-12{suffix}"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"corrupted")
    assert install_tool("clang-format", "12", str(tmp_path), True)
    asset = clang_tools_binary_url("clang-format", "12").rsplit("/", 1)[-1]
    assert stored.read_bytes() == fake_release.published(asset)


def test_install_tool_rejects_corrupted_headers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
):
    """Test that headers not matching the published checksum are an error."""
    monkeypatch.chdir(tmp_path)
    fake_release.serve("clang-resource-headers-21.tar.gz", b"not the archive")
    with pytest.raises(PyPIFallback, match="corrupted during download"):
        install_tool("clang-tidy", "21", str(tmp_path / "bin"), True)
    assert not (data_root / "llvm-21.1.0" / "lib").exists()
    assert sorted(p.name for p in (data_root / "llvm-21.1.0").iterdir()) == ["bin"]


def test_install_tool_invalid_tag(tmp_path: Path, fake_release):
    """Test that a release tag from the index can't point outside the data dir."""
    fake_release._index()["versions"]["21"]["tag"] = "../../escape"
    with pytest.raises(PyPIFallback, match="Invalid release tag"):
        install_tool("clang-format", "21", str(tmp_path), True)


@pytest.mark.parametrize("has_archive", [True, False])
def test_install_tool_tag_headers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_release,
    data_root: Path,
    capsys,
    has_archive: bool,
):
    """Test the headers of a release picked with CLANG_TOOLS_TAG, if it has them."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("clang_tools.install.binary_tag", "2026.01.01-abc")
    if not has_archive:  # like the releases from before the headers existed
        fake_release.sha512sums = "".join(
            line
            for line in fake_release._sha512sums().splitlines(keepends=True)
            if "clang-resource-headers" not in line
        )
    assert install_tool("clang-tidy", "21", str(tmp_path), True)
    headers = data_root / "2026.01.01-abc" / "lib" / "clang" / "21" / "include"
    assert (headers / "stddef.h").is_file() is has_archive
    warning = "has no clang resource headers" in capsys.readouterr().err
    assert warning is not has_archive


def test_install_headers_parallel_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
):
    """Test that headers installed meanwhile by another process are kept."""
    monkeypatch.chdir(tmp_path)
    existing = data_root / "llvm-21.1.0" / "lib" / "clang" / "21" / "include"
    existing.mkdir(parents=True)
    (existing / "stddef.h").write_bytes(b"from the other process")
    # the other process finished after this one checked
    monkeypatch.setattr("clang_tools.install.has_headers", lambda prefix, major: False)
    assert install_tool("clang-tidy", "21", str(tmp_path), True)
    assert (existing / "stddef.h").read_bytes() == b"from the other process"
    assert sorted(p.name for p in (data_root / "llvm-21.1.0").iterdir()) == [
        "bin",
        "lib",
    ]


@pytest.mark.parametrize(
    "entries",
    [
        {"lib/clang/21/include/../../../../escape.h": b"x"},
        {"/lib/clang/21/include/stddef.h": b"x"},
        {"lib/other/21/include/stddef.h": b"x"},
        {"lib/clang/stddef.h": b"x"},
        {"lib/clang/21/include/stddef.h": b"x", "lib/clang/22/include/x.h": b"x"},
        {"lib": None},
        {"lib/clang/21/include/x\\..\\..\\..\\..\\escape.h": b"x"},
        {"lib/clang/21/include/C:/escape.h": b"x"},
    ],
    ids=[
        "dotdot",
        "absolute",
        "not-clang",
        "no-version",
        "two-versions",
        "empty",
        "backslash",
        "drive",
    ],
)
def test_extract_headers_rejects(tmp_path: Path, entries: dict):
    """Test that an archive can only add the headers of one version."""
    archive = tmp_path / "headers.tar.gz"
    archive.write_bytes(make_tar(entries))
    with pytest.raises(PyPIFallback):
        extract_headers(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_extract_headers_rejects_links(tmp_path: Path):
    """Test that an archive can't hold a symbolic link."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        link = tarfile.TarInfo("lib/clang/21/include/stddef.h")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar.addfile(link)
    archive = tmp_path / "headers.tar.gz"
    archive.write_bytes(buffer.getvalue())
    with pytest.raises(PyPIFallback, match="Unexpected entry"):
        extract_headers(archive, tmp_path / "out")


def test_link_binary_copies_without_symlinks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    """Test the copy used where links can't be made (Windows without Developer Mode).

    clang looks for the headers next to the copy then.
    """
    prefix = tmp_path / "data" / "llvm-21.1.0"
    stored = prefix / "bin" / "clang-tidy-21"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"binary")
    headers = prefix / "lib" / "clang" / "21" / "include"
    headers.mkdir(parents=True)
    (headers / "stddef.h").write_bytes(b"header")
    install_dir = tmp_path / "venv" / "Scripts"
    install_dir.mkdir(parents=True)

    def refuse(self, target, target_is_directory=False):
        raise OSError(1, "symlinks are not allowed")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    link_binary(stored, install_dir / "clang-tidy-21")
    assert (install_dir / "clang-tidy-21").read_bytes() == b"binary"
    copied = tmp_path / "venv" / "lib" / "clang" / "21" / "include" / "stddef.h"
    assert copied.read_bytes() == b"header"
    assert "Copying the clang resource headers to" in capsys.readouterr().out

    # a tool without headers is just copied
    (install_dir / "clang-tidy-21").unlink()
    other = tmp_path / "data" / "tag" / "bin" / "clang-format-21"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"format")
    link_binary(other, install_dir / "clang-format-21")
    assert (install_dir / "clang-format-21").read_bytes() == b"format"


@pytest.mark.parametrize("os_name", ["windows", "linux"])
def test_link_binary_headers_next_to_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, os_name: str
):
    """Test that on Windows the headers are also next to the link.

    clang 12 to 17 on Windows (at least) look for them there, not next to the linked binary.
    """
    monkeypatch.setattr("clang_tools.install.install_os", os_name)
    prefix = tmp_path / "data" / "llvm-15.0.2"
    stored = prefix / "bin" / "clang-tidy-15"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"binary")
    headers = prefix / "lib" / "clang" / "15.0.2" / "include"
    headers.mkdir(parents=True)
    (headers / "stddef.h").write_bytes(b"header")
    install_dir = tmp_path / "venv" / "Scripts"
    install_dir.mkdir(parents=True)

    link_binary(stored, install_dir / "clang-tidy-15")
    assert (install_dir / "clang-tidy-15").resolve() == stored.resolve()
    copied = tmp_path / "venv" / "lib" / "clang" / "15.0.2" / "include" / "stddef.h"
    assert copied.is_file() is (os_name == "windows")
    capsys.readouterr()

    # already there: nothing to do
    link_binary(stored, install_dir / "clang-tidy-15")
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "os_name,env,expected",
    [
        ("linux", {"XDG_DATA_HOME": "xdg"}, "xdg/clang-tools"),
        ("linux", {}, "home/.local/share/clang-tools"),
        ("macosx", {}, "home/Library/Application Support/clang-tools"),
        ("windows", {"LOCALAPPDATA": "local"}, "local/clang-tools"),
        ("windows", {}, "home/AppData/Local/clang-tools"),
        ("linux", {"CLANG_TOOLS_DATA_DIR": "custom"}, "custom"),
    ],
)
def test_data_dir_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    os_name: str,
    env: dict,
    expected: str,
):
    """Test the default data directory of each OS."""
    monkeypatch.chdir(tmp_path)
    for name in ("CLANG_TOOLS_DATA_DIR", "XDG_DATA_HOME", "LOCALAPPDATA"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, str(tmp_path / value))
    monkeypatch.setattr(
        "os.path.expanduser", lambda p: str(tmp_path / "home" / p.removeprefix("~/"))
    )
    monkeypatch.setattr("clang_tools.install.install_os", os_name)
    assert data_dir() == Path(os.path.realpath(tmp_path / expected))


def test_data_dir_not_writable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release
):
    """Test the message when the data directory can't be created."""
    not_a_dir = tmp_path / "file"
    not_a_dir.write_bytes(b"not a directory")
    monkeypatch.setenv("CLANG_TOOLS_DATA_DIR", str(not_a_dir))
    with pytest.raises(SystemExit, match="Set CLANG_TOOLS_DATA_DIR"):
        install_tool("clang-format", "21", str(tmp_path), True)


def test_install_clang_tools_replaces_old_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_release, data_root: Path
):
    """Test that a binary copied by an older clang-tools is replaced by a link.

    The old copy has no headers next to it, so it is not used as a native binary.
    """
    monkeypatch.chdir(tmp_path)
    old_copy = tmp_path / f"clang-tidy-21{suffix}"
    old_copy.write_bytes(b"copied by clang-tools 1.x")
    monkeypatch.setattr(
        "clang_tools.install.is_installed", lambda tool, ver: old_copy.resolve()
    )
    install_clang_tools(Version("21"), ["clang-tidy"], str(tmp_path), False, True)
    assert old_copy.is_symlink()
    assert old_copy.resolve().is_relative_to(data_root)


def test_is_managed(tmp_path: Path, data_root: Path):
    """Test which binaries found in PATH are reinstalled."""
    install_dir = str(tmp_path / "bin")
    assert is_managed(tmp_path / "bin" / "clang-tidy-21", install_dir)
    assert is_managed(data_root / "llvm-21.1.0" / "bin" / "clang-tidy-21", install_dir)
    assert not is_managed(Path("/usr/lib/llvm-21/bin/clang-tidy"), install_dir)


def test_uninstall_tool_removes_dangling_link(tmp_path: Path):
    """Test that a link to a binary removed from the data directory is removed."""
    link = tmp_path / f"clang-tidy-21{suffix}"
    link.symlink_to(tmp_path / "data" / "gone")
    uninstall_tool("clang-tidy", "21", str(tmp_path))
    assert not os.path.lexists(link)
