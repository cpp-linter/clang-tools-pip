"""Shared fixtures for the test suite.

The tests never reach the network. The autouse :func:`fake_release` fixture
replaces ``urllib.request.urlopen`` with an in-memory stand-in for the
clang-tools-static-binaries releases: it serves deterministic "binaries", a
``SHA512SUMS`` file listing their hashes, and an ``index.json`` pointing at
them, like the real releases do.
"""

import gzip
import hashlib
import io
import json
import os
import tarfile
import urllib.request
import zipfile
from collections.abc import Iterator
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from clang_tools import MAX_VERSION, MIN_VERSION, index_url, pypi_url, suffix, util

#: The tools published by the static binaries release (see the README).
RELEASED_TOOLS = (
    "clang-format",
    "clang-tidy",
    "clang-query",
    "clang-apply-replacements",
    "clang-include-cleaner",
    "llvm-cov",
    "llvm-profdata",
    "llvm-symbolizer",
    "clang-scan-deps",
)
#: The platform tags used in the release asset names.
PLATFORMS = (
    "linux-amd64",
    "linux-arm64",
    "macos-amd64",
    "macos-arm64",
    "windows-amd64",
    "windows-arm64",
)
#: The name of every binary in the fake release.
RELEASE_ASSETS = frozenset(
    f"{tool}-{version}_{platform}" + (".exe" if platform.startswith("win") else "")
    for tool in RELEASED_TOOLS
    for version in range(MIN_VERSION, MAX_VERSION + 1)
    for platform in PLATFORMS
)

#: The clang resource headers archive of every version in the fake release.
HEADER_ASSETS = frozenset(
    f"clang-resource-headers-{version}.tar.gz"
    for version in range(MIN_VERSION, MAX_VERSION + 1)
)


def headers_dir_name(major: int) -> str:
    """The resource headers directory of a version, like LLVM names it.

    LLVM 15 and older use the full version, later versions the major version only.
    """
    return f"{major}.1.0" if major <= 15 else str(major)


def make_tar(entries: dict[str, bytes | None]) -> bytes:
    """A deterministic ``.tar.gz``: a `None` value is a directory, bytes a file."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return gzip.compress(buffer.getvalue(), mtime=0)


def headers_archive(major: int) -> bytes:
    """The content of ``clang-resource-headers-<major>.tar.gz``."""
    root = f"lib/clang/{headers_dir_name(major)}"
    return make_tar(
        {
            "lib": None,
            "lib/clang": None,
            root: None,
            f"{root}/include": None,
            f"{root}/include/stddef.h": f"/* stddef.h of LLVM {major} */\n".encode(),
        }
    )


#: The base URL of the fake wheel downloads.
WHEELS_URL = "https://files.pythonhosted.org/packages"
#: The platform tag of the fake wheels. Tests make it the only compatible one.
WHEEL_TAG = "test_platform"


def make_wheel(tool: str, version: str, headers: bool = False) -> bytes:
    """A wheel laid out like the clang tools wheels on PyPI."""
    package = tool.replace("-", "_")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as wheel:
        wheel.writestr(f"{package}/__init__.py", "")
        wheel.writestr(f"{package}/data/bin/", "")
        wheel.writestr(f"{package}/data/bin/{tool}{suffix}", f"{tool} {version}\n")
        wheel.writestr(f"{package}/data/bin/{tool}-diff.py", "print()\n")
        if headers:
            include = f"{package}/data/lib/clang/{version.split('.')[0]}/include"
            wheel.writestr(f"{include}/stddef.h", "/* stddef.h */\n")
        wheel.writestr(f"{package}/data/share/README", "not installed\n")
        wheel.writestr(f"{package}-{version}.dist-info/RECORD", "")
    return buffer.getvalue()


#: The base URL of the fake per-version releases.
RELEASES_URL = "https://github.com/cpp-linter/clang-tools-static-binaries/releases"


class FakeResponse(io.BytesIO):
    """The part of :class:`http.client.HTTPResponse` that the package uses.

    :param data: The response body.
    :param status: The HTTP status code.
    :param length: The advertised ``Content-Length`` (defaults to ``len(data)``).
    """

    def __init__(
        self,
        data: bytes,
        status: int = 200,
        length: int | None = None,
        content_type: str = "application/octet-stream",
        url: str = "",
    ):
        super().__init__(data)
        self.status = status
        self.length = len(data) if length is None else length
        self.empty_reads = 0
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.url = url

    def geturl(self) -> str:
        """The URL of the response, after redirects."""
        return self.url

    def read(self, size: int | None = -1) -> bytes:
        """Read like a socket, but fail instead of looping forever at the end."""
        data = super().read(size)
        if not data:
            self.empty_reads += 1
            assert self.empty_reads < 100, "read() keeps being called after the end"
        return data


class FakeRelease:
    """An in-memory stand-in for the static binaries' GitHub release."""

    def __init__(self) -> None:
        #: Every ``(url, timeout)`` passed to ``urlopen``, in order.
        self.requests: list[tuple[str, float | None]] = []
        #: The HTTP headers of each request, in the same order.
        self.request_headers: list[dict[str, str]] = []
        #: Replaces the generated ``SHA512SUMS`` content when not `None`.
        self.sha512sums: str | None = None
        #: Replaces the generated ``index.json`` content when not `None`.
        self.index: dict | None = None
        self._served: dict[str, tuple[bytes, int, int | None]] = {}
        #: The files of each project on the fake PyPI, as in its simple JSON API.
        self.pypi: dict[str, list[dict]] = {}
        #: Serve the PEP 503 HTML pages instead of the PEP 691 JSON ones.
        self.pypi_html = False
        self._wheels: dict[str, bytes] = {}

    def add_wheel(
        self,
        tool: str,
        version: str,
        tag: str = WHEEL_TAG,
        data: bytes | None = None,
        **info,
    ) -> dict:
        """Publish a wheel on the fake PyPI and return its file information."""
        data = (
            make_wheel(tool, version, headers=tool == "clang-tidy")
            if data is None
            else data
        )
        name = f"{tool.replace('-', '_')}-{version}-py2.py3-none-{tag}.whl"
        self._wheels[name] = data
        file = {
            "filename": name,
            "url": f"{WHEELS_URL}/{name}",
            "hashes": {"sha256": hashlib.sha256(data).hexdigest()},
            "yanked": False,
            **info,
        }
        self.pypi.setdefault(tool, []).append(file)
        return file

    def _project_page(self, project: str, url: str) -> FakeResponse:
        """A project page of the simple repository API (PEP 691 or PEP 503)."""
        files = self.pypi[project]
        if not self.pypi_html:
            body = {"meta": {"api-version": "1.1"}, "name": project, "files": files}
            return FakeResponse(
                json.dumps(body).encode(),
                content_type="application/vnd.pypi.simple.v1+json",
                url=url,
            )
        links = "".join(
            f'<a href="{file["url"]}'
            + (f"#sha256={file['hashes']['sha256']}" if file["hashes"] else "")
            + '"'
            + (' data-yanked=""' if file["yanked"] else "")
            + f">{file['filename']}</a><br/>\n"
            for file in files
        )
        page = f"<!DOCTYPE html><html><body><h1>{project}</h1>{links}</body></html>"
        return FakeResponse(page.encode(), content_type="text/html", url=url)

    @staticmethod
    def published(name: str) -> bytes:
        """The content of the asset *name*, as listed in ``SHA512SUMS``."""
        if name in HEADER_ASSETS:
            return headers_archive(int(name.rsplit("-", 1)[1].split(".")[0]))
        return f"fake binary {name}\n".encode() * 8

    def serve(
        self, name: str, data: bytes, status: int = 200, length: int | None = None
    ) -> None:
        """Answer requests for the asset *name* with *data*.

        This does not change the ``SHA512SUMS`` file, so serving other bytes
        for a published binary simulates a corrupted or tampered download.
        """
        self._served[name] = (data, status, length)

    def downloads(self) -> list[str]:
        """The names of the assets (including ``SHA512SUMS``) requested so far."""
        return [url.rstrip("/").rsplit("/", 1)[-1] for url, _ in self.requests]

    def urlopen(self, url: str | Request, timeout: float | None = None) -> FakeResponse:
        """Answer like ``urllib.request.urlopen`` would for a release URL."""
        headers = dict(url.header_items()) if isinstance(url, Request) else {}
        url = url.full_url if isinstance(url, Request) else url
        self.requests.append((url, timeout))
        self.request_headers.append(headers)
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"unknown url type: {url!r}")
        if url == index_url:
            return FakeResponse(json.dumps(self._index()).encode())
        if url.startswith(f"{pypi_url}/") and url.endswith("/"):
            project = url.split("/")[-2]
            if project not in self.pypi:
                raise HTTPError(url, 404, "Not Found", Message(), None)
            return self._project_page(project, url)
        if url.startswith(f"{WHEELS_URL}/"):
            name = url.rsplit("/", 1)[-1]
            if name in self._served:
                return FakeResponse(self._served[name][0])
            return FakeResponse(self._wheels[name])
        if "/releases/download/" not in url:
            raise AssertionError(f"unexpected network access in a test: {url}")
        name = url.rsplit("/", 1)[-1]
        if name in self._served:
            data, status, length = self._served[name]
        elif name == "SHA512SUMS":
            data, status, length = self._sha512sums().encode(), 200, None
        elif name in RELEASE_ASSETS or name in HEADER_ASSETS:
            data, status, length = self.published(name), 200, None
        else:
            data, status, length = b"Not Found", 404, None
        if status >= 400:  # like urllib's default error handling
            raise HTTPError(url, status, "Error", {}, None)
        return FakeResponse(data, status, length)

    def _index(self) -> dict:
        if self.index is None:
            versions: dict[str, dict] = {}
            for name in sorted(RELEASE_ASSETS):
                tool_version, platform = name.removesuffix(".exe").rsplit("_", 1)
                tool, version = tool_version.rsplit("-", 1)
                tag = f"llvm-{version}.1.0"
                entry = versions.setdefault(
                    version, {"version": f"{version}.1.0", "tag": tag, "tools": {}}
                )
                entry["tools"].setdefault(tool, {})[platform] = {
                    "name": name,
                    "url": f"{RELEASES_URL}/download/{tag}/{name}",
                    "sha512": hashlib.sha512(self.published(name)).hexdigest(),
                }
            for version, entry in versions.items():
                name = f"clang-resource-headers-{version}.tar.gz"
                entry["resource_headers"] = {
                    "name": name,
                    "url": f"{RELEASES_URL}/download/{entry['tag']}/{name}",
                    "sha512": hashlib.sha512(self.published(name)).hexdigest(),
                }
            self.index = {"schema_version": 1, "versions": versions}
        return self.index

    def _sha512sums(self) -> str:
        if self.sha512sums is None:
            self.sha512sums = "".join(
                f"{hashlib.sha512(self.published(name)).hexdigest()}  {name}\n"
                for name in sorted(RELEASE_ASSETS | HEADER_ASSETS)
            )
        return self.sha512sums


@pytest.fixture(autouse=True)
def fake_release(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRelease]:
    """Serve release downloads from memory instead of the network."""
    release = FakeRelease()
    monkeypatch.setattr(urllib.request, "urlopen", release.urlopen)
    util._fetch_sha512sums.cache_clear()
    util.fetch_index.cache_clear()
    yield release
    util._fetch_sha512sums.cache_clear()
    util.fetch_index.cache_clear()


@pytest.fixture(autouse=True)
def data_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """Keep the downloaded binaries and headers out of the user's data directory."""
    path = tmp_path_factory.mktemp("data")
    monkeypatch.setenv("CLANG_TOOLS_DATA_DIR", str(path))
    return path.resolve()


@pytest.fixture
def outside_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, data_root: Path
) -> Path:
    """An install directory outside the home directory, like ``/usr/local/bin``.

    ``CLANG_TOOLS_DATA_DIR`` is not set, so the tools are copied there.

    :returns: The install directory, ``<tmp_path>/usr/bin``.
    """
    monkeypatch.delenv("CLANG_TOOLS_DATA_DIR")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    install_dir = tmp_path / "usr" / "bin"
    install_dir.mkdir(parents=True)
    return Path(os.path.realpath(install_dir))
