"""Tests related to the utility functions."""

import hashlib
import urllib.request
from pathlib import Path, PurePath
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from clang_tools import install_arch, install_os, suffix
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import (
    Version,
    check_install_arch,
    check_install_os,
    download_file,
    get_sha_checksum,
    verify_sha512,
)


def test_check_install_os():
    """Tests the return value of `check_install_os()`."""
    current_os = check_install_os()
    assert current_os in ("linux", "windows", "macosx")


def test_check_install_arch():
    """Tests the return value of `check_install_arch()`."""
    current_arch = check_install_arch()
    assert current_arch in ("amd64", "arm64")


def test_download_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test that deliberately fails to download a file."""
    monkeypatch.chdir(str(tmp_path))
    url = clang_tools_binary_url("clang-format", "21")
    file_name = download_file(url, "file.tar.gz", True)
    assert file_name is not None


def test_get_sha(monkeypatch: pytest.MonkeyPatch, fake_release):
    """Test the get_sha() function used to fetch the
    releases' corresponding SHA512 checksum from the single SHA512SUMS file."""
    monkeypatch.chdir(PurePath(__file__).parent.as_posix())
    # the (fake) release serves a copy of a real SHA512SUMS file
    fake_release.sha512sums = Path("SHA512SUMS").read_text(encoding="utf-8")
    if install_os == "macosx":
        platform_str = "macos-arm64" if install_arch == "arm64" else "macos-amd64"
    else:  # pragma: no cover
        platform_str = (  # pragma: no cover
            f"{install_os}-arm64"
            if install_arch == "arm64"
            else f"{install_os}-amd64"  # pragma: no cover
        )  # pragma: no cover
    binary_name = f"clang-format-21_{platform_str}{suffix}"
    sha_content = Path("SHA512SUMS").read_text(encoding="utf-8")
    expected_hash = None
    for line in sha_content.splitlines():
        line = line.strip()
        parts = line.rsplit("  ", 1)
        if len(parts) == 2 and parts[1] == binary_name:
            expected_hash = parts[0]
            break
    assert expected_hash is not None, f"Could not find {binary_name} in SHA512SUMS"
    url = clang_tools_binary_url("clang-format", "21")
    actual = get_sha_checksum(url)
    # Compare only the hash portion, ignoring trailing filename and line endings
    actual_hash = actual.strip().split(" ", 1)[0]
    assert actual_hash == expected_hash


def test_get_sha_value_error(monkeypatch: pytest.MonkeyPatch):
    """Test get_sha_checksum raises ValueError when the binary is not found
    in the SHA512SUMS file."""
    monkeypatch.setattr(
        "clang_tools.util._fetch_sha512sums",
        Mock(return_value="somehash  some-other-file"),
    )
    with pytest.raises(
        ValueError, match="Could not find SHA512 checksum for my-binary"
    ):
        get_sha_checksum("https://example.com/release/my-binary")


def test_version_path():
    """Tests version parsing when given specification is a path."""
    version = str(Path(__file__).parent)
    assert Version(version).info == (0, 0, 0)


def test_version_non_numeric():
    """Tests version parsing when given specification is non-numeric."""
    assert Version("abc").info == (0, 0, 0)
    assert Version("12.abc").info == (0, 0, 0)


def test_version_full_semver():
    """Tests version parsing with full semver specification."""
    v = Version("14.0.1")
    assert v.info == (14, 0, 1)
    assert v.string == "14.0.1"


def test_version_major_only():
    """Tests version parsing with only major version."""
    v = Version("15")
    assert v.info == (15, 0, 0)


def test_version_major_minor():
    """Tests version parsing with major.minor."""
    v = Version("15.3")
    assert v.info == (15, 3, 0)


def test_verify_sha512_valid():
    """Tests that sha512 verification returns True for matching hash."""
    data = b"test binary data"
    checksum = hashlib.sha512(data).hexdigest()
    assert verify_sha512(checksum, data)


def test_verify_sha512_invalid():
    """Tests that sha512 verification returns False for non-matching hash."""
    data = b"test binary data"
    checksum = hashlib.sha512(b"different data").hexdigest()
    assert not verify_sha512(checksum, data)


def test_verify_sha512_with_filename_in_checksum():
    """Tests that sha512 verification works when checksum includes a filename."""
    data = b"test binary data"
    checksum = hashlib.sha512(data).hexdigest() + "  clang-format-21_linux-amd64"
    assert verify_sha512(checksum, data)


def test_download_file_http_error(monkeypatch: pytest.MonkeyPatch):
    """Tests that download_file returns None on HTTP error."""
    monkeypatch.setattr(
        "clang_tools.util.urllib.request.urlopen",
        Mock(side_effect=HTTPError("http://fake", 404, "Not Found", {}, None)),
    )
    result = download_file("http://fake/file.tar.gz", "file.tar.gz", True)
    assert result is None


def test_download_file_value_error(monkeypatch: pytest.MonkeyPatch):
    """Tests that download_file returns None on ValueError (invalid URL)."""
    monkeypatch.setattr(
        "clang_tools.util.urllib.request.urlopen",
        Mock(side_effect=ValueError("invalid URL")),
    )
    result = download_file("not-a-url", "file.tar.gz", True)
    assert result is None


def test_download_file_bad_status(monkeypatch: pytest.MonkeyPatch):
    """Tests that download_file returns None when HTTP status is not 200."""
    mock_response = Mock()
    mock_response.status = 404
    monkeypatch.setattr(
        "clang_tools.util.urllib.request.urlopen",
        Mock(return_value=mock_response),
    )
    result = download_file("http://fake/file.tar.gz", "file.tar.gz", True)
    assert result is None


def test_download_file_with_progress_bar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Tests download_file with progress bar enabled (no_progress_bar=False)."""
    monkeypatch.chdir(str(tmp_path))
    url = clang_tools_binary_url("clang-format", "21")
    file_name = download_file(url, "file.tar.gz", False)
    assert file_name is not None


def test_check_install_os_unsupported(monkeypatch: pytest.MonkeyPatch):
    """Tests that check_install_os raises OSError for unsupported OS."""
    monkeypatch.setattr("platform.system", lambda: "SunOS")
    with pytest.raises(OSError, match="sunos is not currently supported"):
        check_install_os()


def test_check_install_arch_amd64(monkeypatch: pytest.MonkeyPatch):
    """Tests check_install_arch returns 'amd64' for x86_64 machines."""
    monkeypatch.setattr("platform.machine", lambda: "x86_64")
    assert check_install_arch() == "amd64"


@pytest.mark.parametrize(
    "system,expected",
    [("Linux", "linux"), ("Darwin", "macosx"), ("Windows", "windows")],
)
def test_check_install_os_names(
    monkeypatch: pytest.MonkeyPatch, system: str, expected: str
):
    """Tests that the OS name is normalized for the release asset names."""
    monkeypatch.setattr("platform.system", lambda: system)
    assert check_install_os() == expected


@pytest.mark.parametrize(
    "machine,expected",
    [
        ("arm64", "arm64"),
        ("aarch64", "arm64"),
        ("ARM64", "arm64"),
        ("AMD64", "amd64"),
        ("x86_64", "amd64"),
    ],
)
def test_check_install_arch_names(
    monkeypatch: pytest.MonkeyPatch, machine: str, expected: str
):
    """Tests that the CPU name is normalized for the release asset names."""
    monkeypatch.setattr("platform.machine", lambda: machine)
    assert check_install_arch() == expected


def test_download_file_saves_content(tmp_path: Path, fake_release, capsys):
    """Tests that download_file saves the served bytes and returns the path."""
    url = clang_tools_binary_url("clang-format", "21")
    destination = tmp_path / "downloaded"
    assert download_file(url, str(destination), True) == destination.as_posix()
    asset = url.rsplit("/", 1)[-1]
    assert destination.read_bytes() == fake_release.published(asset)
    assert capsys.readouterr().out == ""  # no progress bar


@pytest.mark.parametrize("os_name,bar", [("linux", "█"), ("windows", "=")])
def test_download_file_progress_bar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_release,
    capsys,
    os_name: str,
    bar: str,
):
    """Tests the progress bar from 0% to 100% (ASCII on Windows)."""
    monkeypatch.setattr("clang_tools.util.check_install_os", lambda: os_name)
    url = clang_tools_binary_url("clang-format", "21")
    download_file(url, str(tmp_path / "downloaded"), False)
    size = len(fake_release.published(url.rsplit("/", 1)[-1]))
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"    |{' ' * 20}| 0% (of {size} bytes)"
    assert lines[-1] == f"\033[F    |{bar * 20}| 100% (of {size} bytes)"


def test_get_sha_checksum_exact_name(fake_release):
    """Tests that only the line for this exact binary name is used."""
    base = "https://example.com/releases/download/tag"
    expected = "a" * 128
    fake_release.sha512sums = "\r\n".join(
        [
            f"{'b' * 128}  clang-format-21_linux-amd64.exe",
            f"{'c' * 128}  xclang-format-21_linux-amd64",
            "a line that is not a checksum",
            "",
            f"{expected}  clang-format-21_linux-amd64",
            f"{'d' * 128}  clang-format-21_linux-amd64.sig",
        ]
    )
    assert get_sha_checksum(f"{base}/clang-format-21_linux-amd64") == expected
    assert fake_release.downloads() == ["SHA512SUMS"]
    assert fake_release.requests[0][0] == f"{base}/SHA512SUMS"


def test_get_sha_checksum_fetches_sums_once(fake_release):
    """Tests that SHA512SUMS is fetched once, with a timeout, for all binaries."""
    base = "https://example.com/releases/download/tag"
    format_sum = get_sha_checksum(f"{base}/clang-format-12_linux-amd64")
    tidy_sum = get_sha_checksum(f"{base}/clang-tidy-12_linux-amd64")
    assert format_sum != tidy_sum
    assert len(fake_release.requests) == 1
    url, timeout = fake_release.requests[0]
    assert url == f"{base}/SHA512SUMS"
    assert timeout is not None and timeout > 0


def test_get_sha_checksum_missing_sums_file(fake_release):
    """Tests that a release without a SHA512SUMS file is an error."""
    fake_release.serve("SHA512SUMS", b"Not Found", status=404)
    with pytest.raises(HTTPError):
        get_sha_checksum("https://example.com/releases/download/tag/clang-format-12")


def test_verify_sha512_empty_checksum():
    """Tests that an empty checksum never verifies."""
    assert not verify_sha512("", b"test binary data")


def test_network_is_disabled():
    """Tests that requests other than release downloads never leave the machine."""
    with pytest.raises(AssertionError, match="unexpected network access"):
        urllib.request.urlopen("https://pypi.org/pypi/clang-format/json", timeout=1)


def test_download_file_timeout(tmp_path: Path, fake_release):
    """Tests that the binary download cannot wait forever on a stalled server."""
    url = clang_tools_binary_url("clang-format", "21")
    assert download_file(url, str(tmp_path / "downloaded"), True)
    assert fake_release.requests[-1][0] == url
    timeout = fake_release.requests[-1][1]
    assert timeout is not None and timeout > 0


def test_download_file_truncated(tmp_path: Path, fake_release):
    """Tests that a response cut short is a failed download, not an endless loop."""
    url = clang_tools_binary_url("clang-format", "21")
    fake_release.serve(url.rsplit("/", 1)[-1], b"x" * 40, length=100)
    destination = tmp_path / "downloaded"
    assert download_file(url, str(destination), True) is None
    assert not destination.exists()


@pytest.mark.parametrize("size", [1, 19])
def test_download_file_small(tmp_path: Path, fake_release, size: int):
    """Tests files smaller than the progress bar's 20 steps."""
    url = clang_tools_binary_url("clang-format", "21")
    fake_release.serve(url.rsplit("/", 1)[-1], b"x" * size)
    destination = tmp_path / "downloaded"
    assert download_file(url, str(destination), False) == destination.as_posix()
    assert destination.read_bytes() == b"x" * size
