"""
``clang_tools.wheel_install``
-----------------------------

Install a clang tool from its wheel on PyPI, without pip.

The wheel is found with the simple repository API of PyPI or a mirror (the JSON form
of PEP 691, or the HTML form of PEP 503), checked against its SHA256 checksum, and its
``<package>/data`` folder (``bin/`` and, for clang-tidy, ``lib/clang/``) is
kept in the data directory, like a static binary. The install directory gets a link
to the executable.
"""

import base64
import hashlib
import json
import platform
import re
import tempfile
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import NamedTuple
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from . import install_arch, install_os, pypi_url, suffix
from .install import (
    RE_ENTRY_NAME,
    binary_file_name,
    data_dir,
    link_binary,
    make_dir,
    no_permission,
    uses_data_dir,
)
from .util import (
    DOWNLOAD_ERRORS,
    DOWNLOAD_TIMEOUT,
    RE_VERSION,
    PyPIFallback,
    download_file,
    major_version,
    version_matches,
)

#: The tools with a wheel on PyPI, and the import name of each wheel's package. No
#: other project is downloaded, even if PyPI has one with the tool's name.
WHEEL_TOOLS = {
    "clang-format": "clang_format",
    "clang-tidy": "clang_tidy",
    "clang-include-cleaner": "clang_include_cleaner",
    "clang-apply-replacements": "clang_apply_replacements",
}

#: The glibc versions of the legacy ``manylinux`` tags.
LEGACY_MANYLINUX = {
    "manylinux1": (2, 5),
    "manylinux2010": (2, 12),
    "manylinux2014": (2, 17),
}
RE_MANYLINUX = re.compile(r"(manylinux|musllinux)_(\d+)_(\d+)_(\w+)")
RE_MACOSX = re.compile(r"macosx_(\d+)_(\d+)_(\w+)")


def _major_minor(version: str) -> tuple[int, ...]:
    """The first two numbers of a version, such as ``(2, 39)`` for glibc 2.39.

    A missing or unparsable version is ``(0,)``.
    """
    return tuple(int(n) for n in re.findall(r"\d+", version)[:2]) or (0,)


def is_compatible(tag: str) -> bool:
    """Check if a wheel's platform tag (such as ``win_amd64``) runs on this machine."""
    if install_os == "windows":
        windows = {"amd64": "win_amd64", "arm64": "win_arm64", "i686": "win32"}
        return tag == windows.get(install_arch)
    if install_os == "macosx":
        match = RE_MACOSX.fullmatch(tag)
        arch = {"amd64": "x86_64", "arm64": "arm64"}.get(install_arch)
        return (
            match is not None
            and match[3] in (arch, "universal2")
            and (int(match[1]), int(match[2])) <= _major_minor(platform.mac_ver()[0])
        )
    # other architectures, such as ppc64le and s390x, have the same name in wheel tags
    arch = {"amd64": "x86_64", "arm64": "aarch64"}.get(install_arch, install_arch)
    libc, libc_version = platform.libc_ver()
    glibc = libc == "glibc"
    legacy, _, legacy_arch = tag.partition("_")
    if legacy in LEGACY_MANYLINUX:
        return (
            glibc
            and legacy_arch == arch
            and (LEGACY_MANYLINUX[legacy] <= _major_minor(libc_version))
        )
    match = RE_MANYLINUX.fullmatch(tag)
    if match is None or match[4] != arch:
        return False
    if match[1] == "musllinux":
        return not glibc
    return glibc and (int(match[2]), int(match[3])) <= _major_minor(libc_version)


#: Ask for the JSON form of the simple repository API (PEP 691), else its HTML form.
SIMPLE_API_ACCEPT = (
    "application/vnd.pypi.simple.v1+json,"
    " application/vnd.pypi.simple.v1+html;q=0.2, text/html;q=0.01"
)
SIMPLE_API_JSON = "application/vnd.pypi.simple.v1+json"


class WheelFile(NamedTuple):
    """A wheel listed by the package index."""

    #: The file name, such as ``clang_format-21.1.8-py2.py3-none-win_amd64.whl``.
    filename: str
    #: The download URL.
    url: str
    #: The SHA256 checksum, or an empty string if the index doesn't give one.
    sha256: str
    #: Whether the file was yanked (PEP 592).
    yanked: bool


def split_credentials(url: str) -> tuple[str, dict[str, str]]:
    """Take the user name and password out of a URL, as an ``Authorization`` header.

    :returns: The URL without them, and the HTTP headers that send them.
    """
    parts = urlsplit(url)
    if parts.username is None:
        return url, {}
    user_pass = f"{unquote(parts.username)}:{unquote(parts.password or '')}"
    token = base64.b64encode(user_pass.encode()).decode()
    netloc = parts.netloc.rpartition("@")[2]
    return urlunsplit(parts._replace(netloc=netloc)), {
        "Authorization": f"Basic {token}"
    }


class _Anchors(HTMLParser):
    """The links of a PEP 503 project page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[dict[str, str | None], str]] = []
        self._attrs: dict[str, str | None] | None = None
        self._text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._attrs, self._text = dict(attrs), ""

    def handle_data(self, data: str) -> None:
        if self._attrs is not None:
            self._text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._attrs is not None:
            self.links.append((self._attrs, self._text.strip()))
            self._attrs = None


def parse_project_page(body: str, content_type: str, page_url: str) -> list[WheelFile]:
    """The files of a project page of the simple repository API.

    :param body: The page.
    :param content_type: The page's media type: PEP 691 JSON, or else PEP 503 HTML.
    :param page_url: The URL of the page, which relative file URLs are resolved
        against.
    """
    if content_type == SIMPLE_API_JSON:
        return [
            WheelFile(
                file["filename"],
                urljoin(page_url, file["url"]),
                file.get("hashes", {}).get("sha256", ""),
                bool(file.get("yanked")),
            )
            for file in json.loads(body)["files"]
        ]
    parser = _Anchors()
    parser.feed(body)
    files = []
    for attrs, text in parser.links:
        url, _, fragment = urljoin(page_url, attrs.get("href") or "").partition("#")
        algorithm, _, digest = fragment.partition("=")
        files.append(
            WheelFile(
                text,
                url,
                digest if algorithm == "sha256" else "",
                "data-yanked" in attrs,
            )
        )
    return files


def wheel_version(filename: str, tool: str) -> str | None:
    """The version of a wheel of ``tool``, if it is a stable release.

    :returns: The version, such as ``21.1.8``, or `None` for another file.
    """
    if not filename.endswith(".whl"):
        return None
    parts = filename.removesuffix(".whl").split("-")
    if len(parts) not in (5, 6) or re.sub(r"[-_.]+", "-", parts[0]).lower() != tool:
        return None
    return parts[1] if RE_VERSION.fullmatch(parts[1]) else None


def pypi_releases(tool: str) -> dict[str, list[WheelFile]]:
    """The stable releases of a tool on the package index, with their wheels.

    :param tool: The name of the project, such as ``clang-format``.

    :returns: The wheels of each release that only has numbers in its version.
    """
    index, credentials = split_credentials(pypi_url)
    url = f"{index}/{tool}/"
    request = urllib.request.Request(
        url, headers={"Accept": SIMPLE_API_ACCEPT, **credentials}
    )
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            body = response.read().decode(encoding="utf-8")
            files = parse_project_page(
                body, response.headers.get_content_type(), response.geturl()
            )
    except (*DOWNLOAD_ERRORS, KeyError, TypeError) as exc:
        raise SystemExit(f"Can't get the releases of {tool} from {url}: {exc}") from exc
    releases: dict[str, list[WheelFile]] = {}
    for file in files:
        version = wheel_version(file.filename, tool)
        if version is not None:
            releases.setdefault(version, []).append(file)
    return releases


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(map(int, version.split(".")))


def runs_here(file: WheelFile) -> bool:
    """Check if a wheel runs on this machine and was not yanked."""
    tags = file.filename.removesuffix(".whl").rsplit("-", 1)[-1].split(".")
    return not file.yanked and any(is_compatible(tag) for tag in tags)


def no_such_version(tool: str, version: str | None, versions: list[str]) -> SystemExit:
    """The error for a version that the package index doesn't have.

    :param versions: The versions that the index has, listed in the message: those
        of the same major version, else every major version.
    """
    wanted = f"{tool} {version}" if version else f"a release of {tool}"
    same_major = [
        v for v in versions if version and major_version(v) == major_version(version)
    ]
    available = sorted(
        same_major or {major_version(v) for v in versions}, key=_version_key
    )
    return SystemExit(
        f"{pypi_url_shown()} has no {wanted}."
        + (f" Available versions: {', '.join(available)}." if available else "")
    )


def find_wheel(tool: str, version: str | None) -> tuple[str, WheelFile]:
    """Find the newest wheel of a tool that runs on this machine.

    :param tool: The name of the project on the package index.
    :param version: The version to install, such as ``21`` or ``21.1.8``, or `None`
        for the newest one.

    :returns: The version and the wheel.
    """
    releases = pypi_releases(tool)
    candidates = sorted(
        (v for v in releases if version is None or version_matches(version, v)),
        key=_version_key,
        reverse=True,
    )
    if not candidates:
        raise no_such_version(tool, version, list(releases))
    for candidate in candidates:
        file = next(filter(runs_here, releases[candidate]), None)
        if file is not None:
            return candidate, file
    wanted = f"{tool} {version}" if version else tool
    raise SystemExit(
        f"No wheel of {wanted} on {pypi_url_shown()} runs on this machine"
        f" ({install_os} {install_arch})."
    )


def pypi_url_shown() -> str:
    """The package index URL, without a password, for messages."""
    return split_credentials(pypi_url)[0]


def extract_wheel(wheel: Path, package: str, destination: Path) -> None:
    """Extract the ``bin/`` and ``lib/`` folders of a wheel's ``<package>/data``.

    :param wheel: The wheel file.
    :param package: The import name of the package, such as ``clang_format``.
    :param destination: The directory to extract into.
    """
    prefix = f"{package}/data/"
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            parts = PurePosixPath(info.filename.removeprefix(prefix)).parts
            if parts[0] not in ("bin", "lib"):
                continue
            if not all(
                RE_ENTRY_NAME.fullmatch(part) and part != ".." for part in parts
            ):
                raise SystemExit(f"Unexpected entry {info.filename!r} in {wheel.name}")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            if parts[0] == "bin":
                target.chmod(0o755)


def fetch_wheel(
    tool: str, file: WheelFile, work_dir: Path, no_progress_bar: bool
) -> Path:
    """Download a wheel, check it and extract its executable and headers.

    :returns: The directory with the extracted ``bin/`` and ``lib/`` folders.
    """
    wheel = work_dir / "download.whl"
    index, credentials = split_credentials(pypi_url)
    # the password is only sent to the index's own server
    same_server = urlsplit(file.url).netloc == urlsplit(index).netloc
    try:
        download_file(
            file.url, str(wheel), no_progress_bar, credentials if same_server else None
        )
    except PyPIFallback as exc:
        raise SystemExit(str(exc)) from exc
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != file.sha256:
        raise SystemExit(
            f"{file.filename} was corrupted during download from {file.url}"
        )
    extracted = work_dir / "extracted"
    extract_wheel(wheel, WHEEL_TOOLS[tool], extracted)
    if not (extracted / "bin" / f"{tool}{suffix}").is_file():
        raise SystemExit(f"{file.filename} has no {tool}{suffix} executable.")
    return extracted


def install_wheel(
    tool: str, version: str | None, directory: str, no_progress_bar: bool
) -> str:
    """Install a tool from its wheel on PyPI, in the same way as a static binary.

    :param tool: The name of the tool, which is also its project name on PyPI.
    :param version: The version to install, such as ``21`` or ``21.1.8``, or `None`
        for the newest one.
    :param directory: The installation directory.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :returns: The installed version.
    """
    if tool not in WHEEL_TOOLS:
        raise SystemExit(
            f"{tool} has no wheel on PyPI. Wheels are installed for "
            f"{', '.join(WHEEL_TOOLS)}."
        )
    resolved, file = find_wheel(tool, version)
    if not file.sha256:
        raise SystemExit(
            f"{pypi_url_shown()} gives no SHA256 checksum for {file.filename},"
            " so it can't be checked."
        )
    exe_name = f"{tool}{suffix}"
    destination = Path(directory, binary_file_name(tool, major_version(resolved)))
    if uses_data_dir(directory):
        prefix = data_dir() / f"pypi-{tool}-{resolved}"
        exe = prefix / "bin" / exe_name
        if not exe.is_file():
            make_dir(data_dir())
            with tempfile.TemporaryDirectory(dir=data_dir()) as work_dir:
                extracted = fetch_wheel(tool, file, Path(work_dir), no_progress_bar)
                try:
                    # one rename, so the directory is either complete or not there
                    extracted.rename(prefix)
                except OSError:
                    if not exe.is_file():
                        raise  # pragma: no cover (not a parallel install)
        link_binary(exe, destination)
    else:  # a copy, with the headers where clang looks for them
        try:
            with tempfile.TemporaryDirectory(dir=directory) as work_dir:
                extracted = fetch_wheel(tool, file, Path(work_dir), no_progress_bar)
                link_binary(extracted / "bin" / exe_name, destination, copy=True)
        except PermissionError as exc:
            raise no_permission(destination) from exc
    print(f"Installed {tool} {resolved} (from PyPI) as {destination}")
    return resolved
