"""Tests related to the utility functions."""

import hashlib
from pathlib import Path, PurePath
from urllib.error import HTTPError
from unittest.mock import Mock
import pytest
from clang_tools import install_arch, install_os, suffix
from clang_tools.install import clang_tools_binary_url
from clang_tools.util import (
    check_install_arch,
    check_install_os,
    download_file,
    get_sha_checksum,
    verify_sha512,
    Version,
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


def test_get_sha(monkeypatch: pytest.MonkeyPatch):
    """Test the get_sha() function used to fetch the
    releases' corresponding SHA512 checksum from the single SHA512SUMS file."""
    monkeypatch.chdir(PurePath(__file__).parent.as_posix())
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
        if line.endswith("  " + binary_name):
            expected_hash = line.split("  ", 1)[0]
            break
    assert expected_hash is not None, f"Could not find {binary_name} in SHA512SUMS"
    url = clang_tools_binary_url("clang-format", "21")
    actual = get_sha_checksum(url)
    # Compare only the hash portion, ignoring trailing filename and line endings
    actual_hash = actual.strip().split(" ", 1)[0]
    assert actual_hash == expected_hash


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
