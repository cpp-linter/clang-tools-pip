"""Tests for clang_tools.wheel_install: installing wheels from PyPI without pip."""

import io
import os
import zipfile
from pathlib import Path

import pytest
from conftest import WHEEL_TAG, FakeRelease

from clang_tools import suffix
from clang_tools.wheel_install import (
    extract_wheel,
    find_wheel,
    install_wheel,
    is_compatible,
    pypi_releases,
)


@pytest.fixture
def wheels(monkeypatch: pytest.MonkeyPatch, fake_release: FakeRelease) -> FakeRelease:
    """The fake PyPI, where only wheels tagged `WHEEL_TAG` run on this machine."""
    monkeypatch.setattr(
        "clang_tools.wheel_install.is_compatible", lambda tag: tag == WHEEL_TAG
    )
    return fake_release


# ---------------------------------------------------------------------------
#  Platform tags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "os_name,arch,libc,mac,tag,expected",
    [
        ("windows", "amd64", ("", ""), "", "win_amd64", True),
        ("windows", "amd64", ("", ""), "", "win32", False),
        ("windows", "arm64", ("", ""), "", "win_arm64", True),
        ("windows", "arm64", ("", ""), "", "win_amd64", False),
        ("macosx", "arm64", ("", ""), "14.5", "macosx_11_0_arm64", True),
        ("macosx", "arm64", ("", ""), "14.5", "macosx_10_9_universal2", True),
        ("macosx", "arm64", ("", ""), "14.5", "macosx_10_9_x86_64", False),
        ("macosx", "amd64", ("", ""), "10.15", "macosx_10_9_x86_64", True),
        ("macosx", "amd64", ("", ""), "10.15", "macosx_11_0_x86_64", False),
        ("macosx", "amd64", ("", ""), "", "macosx_10_9_x86_64", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "manylinux_2_28_x86_64", True),
        ("linux", "amd64", ("glibc", "2.17"), "", "manylinux_2_28_x86_64", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "manylinux_2_28_aarch64", False),
        ("linux", "arm64", ("glibc", "2.39"), "", "manylinux_2_28_aarch64", True),
        ("linux", "amd64", ("glibc", "2.39"), "", "manylinux2014_x86_64", True),
        ("linux", "amd64", ("glibc", "2.12"), "", "manylinux2014_x86_64", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "manylinux1_i686", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "musllinux_1_2_x86_64", False),
        ("linux", "amd64", ("", ""), "", "musllinux_1_2_x86_64", True),
        ("linux", "amd64", ("", ""), "", "manylinux_2_28_x86_64", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "linux_x86_64", False),
        ("linux", "amd64", ("glibc", "2.39"), "", "any", False),
    ],
)
def test_is_compatible(
    monkeypatch: pytest.MonkeyPatch,
    os_name: str,
    arch: str,
    libc: tuple[str, str],
    mac: str,
    tag: str,
    expected: bool,
):
    """Test which platform tags run on a machine."""
    monkeypatch.setattr("clang_tools.wheel_install.install_os", os_name)
    monkeypatch.setattr("clang_tools.wheel_install.install_arch", arch)
    monkeypatch.setattr("platform.libc_ver", lambda: libc)
    monkeypatch.setattr("platform.mac_ver", lambda: (mac, ("", "", ""), ""))
    assert is_compatible(tag) is expected


# ---------------------------------------------------------------------------
#  Finding a wheel
# ---------------------------------------------------------------------------


def test_pypi_releases_only_stable(wheels: FakeRelease):
    """Test that pre-releases are left out."""
    for version in ("21.1.8", "22.1.0rc1", "22.1.0.dev1", "13.0.1.1"):
        wheels.add_wheel("clang-format", version)
    assert sorted(pypi_releases("clang-format")) == ["13.0.1.1", "21.1.8"]


@pytest.mark.parametrize(
    "body", [b"not json", b'{"no": "releases"}', b"[]"], ids=["json", "key", "type"]
)
def test_pypi_releases_unusable(
    monkeypatch: pytest.MonkeyPatch, wheels: FakeRelease, body: bytes
):
    """Test the message when PyPI answers with something unexpected."""
    from conftest import FakeResponse

    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url, timeout=None: FakeResponse(body)
    )
    with pytest.raises(SystemExit, match="Can't get the releases of clang-format"):
        pypi_releases("clang-format")


def test_pypi_releases_unknown_project(wheels: FakeRelease):
    """Test the message for a tool that is not on PyPI."""
    with pytest.raises(SystemExit, match="HTTP Error 404"):
        pypi_releases("clang-nope")


@pytest.mark.parametrize(
    "version,expected",
    [(None, "210.0.0"), ("21", "21.1.8"), ("21.1", "21.1.8"), ("21.1.0", "21.1.0")],
)
def test_find_wheel_version(wheels: FakeRelease, version: str | None, expected: str):
    """Test that the newest matching version is picked."""
    for v in ("21.1.0", "21.1.8", "22.1.8", "2.0.0", "210.0.0"):
        wheels.add_wheel("clang-format", v)
    assert find_wheel("clang-format", version)[0] == expected


def test_find_wheel_skips_unusable_files(wheels: FakeRelease):
    """Test that yanked files, sdists and other platforms are skipped."""
    wheels.add_wheel("clang-format", "21.1.0")
    wheels.add_wheel("clang-format", "21.1.8", tag="other_platform")
    wheels.add_wheel("clang-format", "21.1.7", yanked=True)
    wheels.pypi["clang-format"]["21.1.6"] = [
        {"filename": "clang_format-21.1.6.tar.gz", "url": "x", "yanked": False}
    ]
    version, file = find_wheel("clang-format", "21")
    assert version == "21.1.0"
    assert file["filename"].endswith(f"-{WHEEL_TAG}.whl")


def test_find_wheel_multiple_tags(wheels: FakeRelease):
    """Test a wheel with several platform tags in its name."""
    wheels.add_wheel("clang-format", "21.1.8", tag=f"other_platform.{WHEEL_TAG}")
    assert find_wheel("clang-format", None)[0] == "21.1.8"


@pytest.mark.parametrize("version", ["99", None])
def test_find_wheel_none(wheels: FakeRelease, version: str | None):
    """Test the message when no wheel runs on this machine."""
    wheels.add_wheel("clang-format", "21.1.8", tag="other_platform")
    wanted = "clang-format 99" if version else "clang-format on"
    with pytest.raises(SystemExit, match=f"No wheel of {wanted}"):
        find_wheel("clang-format", version)


# ---------------------------------------------------------------------------
#  Installing a wheel
# ---------------------------------------------------------------------------


def test_install_wheel(wheels: FakeRelease, tmp_path: Path, data_root: Path, capsys):
    """Test that the wheel's executable is linked from the install directory."""
    wheels.add_wheel("clang-format", "21.1.8")
    assert install_wheel("clang-format", "21", str(tmp_path), True) == "21.1.8"
    prefix = data_root / "pypi-clang-format-21.1.8"
    exe = prefix / "bin" / f"clang-format{suffix}"
    link = tmp_path / f"clang-format-21{suffix}"
    assert link.resolve() == exe.resolve()
    assert link.read_text() == "clang-format 21.1.8\n"
    assert os.access(exe, os.X_OK)
    assert sorted(p.name for p in prefix.iterdir()) == ["bin"]  # not share/
    assert "Installed clang-format 21.1.8 (from PyPI)" in capsys.readouterr().out

    # installing again reuses the extracted wheel
    downloads = len(wheels.requests)
    other = tmp_path / "other"
    other.mkdir()
    install_wheel("clang-format", "21", str(other), True)
    assert wheels.downloads()[downloads:] == ["json"]  # only the release list
    assert (other / f"clang-format-21{suffix}").resolve() == exe.resolve()


def test_install_wheel_headers(wheels: FakeRelease, tmp_path: Path, data_root: Path):
    """Test that clang-tidy's headers are kept next to it, where clang finds them."""
    wheels.add_wheel("clang-tidy", "21.1.8")
    install_wheel("clang-tidy", None, str(tmp_path), True)
    exe = (tmp_path / f"clang-tidy-21{suffix}").resolve()
    assert (exe.parent.parent / "lib/clang/21/include/stddef.h").is_file()


def test_install_wheel_corrupted(wheels: FakeRelease, tmp_path: Path, data_root: Path):
    """Test that a download not matching the checksum on PyPI is an error."""
    file = wheels.add_wheel("clang-format", "21.1.8")
    wheels.serve(file["filename"], b"not the wheel")
    with pytest.raises(SystemExit, match="corrupted during download"):
        install_wheel("clang-format", "21", str(tmp_path), True)
    assert list(data_root.iterdir()) == []
    assert list(tmp_path.iterdir()) == []


def test_install_wheel_download_error(
    monkeypatch: pytest.MonkeyPatch, wheels: FakeRelease, tmp_path: Path
):
    """Test the message when the wheel can't be downloaded."""
    file = wheels.add_wheel("clang-format", "21.1.8")
    real_urlopen = wheels.urlopen

    def urlopen(url, timeout=None):
        if url == file["url"]:
            raise OSError("network is down")
        return real_urlopen(url, timeout)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    with pytest.raises(SystemExit, match="network is down"):
        install_wheel("clang-format", "21", str(tmp_path), True)


def test_install_wheel_without_executable(wheels: FakeRelease, tmp_path: Path):
    """Test a wheel that is laid out differently (like clang-format 6.0.1)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as wheel:
        wheel.writestr("clang_format/__init__.py", "")
    wheels.add_wheel("clang-format", "6.0.1", data=buffer.getvalue())
    with pytest.raises(SystemExit, match=f"has no clang-format{suffix} executable"):
        install_wheel("clang-format", "6", str(tmp_path), True)


@pytest.mark.parametrize("tool", ["clang-query", "../clang-format"])
def test_install_wheel_unknown_tool(wheels: FakeRelease, tmp_path: Path, tool: str):
    """Test that only the known wheels are downloaded, not any project on PyPI."""
    wheels.add_wheel(tool, "21.1.8")
    with pytest.raises(SystemExit, match=f"{tool} has no wheel on PyPI"):
        install_wheel(tool, None, str(tmp_path), True)
    assert wheels.requests == []


@pytest.mark.parametrize(
    "name", ["bin/../../../escape", "bin/C:/escape"], ids=["dotdot", "drive"]
)
def test_extract_wheel_rejects_parent_dirs(tmp_path: Path, name: str):
    """Test that a wheel can't write outside the directory it is extracted to."""
    wheel = tmp_path / "x.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"clang_format/data/{name}", "x")
    with pytest.raises(SystemExit, match="Unexpected entry"):
        extract_wheel(wheel, "clang_format", tmp_path / "out")
    assert not (tmp_path / "escape").exists()


def test_install_wheel_parallel_install(
    monkeypatch: pytest.MonkeyPatch,
    wheels: FakeRelease,
    tmp_path: Path,
    data_root: Path,
):
    """Test that a wheel extracted meanwhile by another process is kept."""
    wheels.add_wheel("clang-format", "21.1.8")
    exe = data_root / "pypi-clang-format-21.1.8" / "bin" / f"clang-format{suffix}"
    real_extract = extract_wheel

    def extract_and_race(wheel, package, destination):
        real_extract(wheel, package, destination)
        exe.parent.mkdir(parents=True)  # the other process finished first
        exe.write_text("from the other process")

    monkeypatch.setattr("clang_tools.wheel_install.extract_wheel", extract_and_race)
    install_wheel("clang-format", "21", str(tmp_path), True)
    assert (
        tmp_path / f"clang-format-21{suffix}"
    ).read_text() == "from the other process"
