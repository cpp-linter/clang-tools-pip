"""Shared fixtures for the test suite.

The tests never reach the network. The autouse :func:`fake_release` fixture
replaces ``urllib.request.urlopen`` with an in-memory stand-in for the
clang-tools-static-binaries release: it serves deterministic "binaries" and a
``SHA512SUMS`` file listing their hashes, like the real release does.
"""

import hashlib
import io
import urllib.request
from collections.abc import Iterator
from urllib.error import HTTPError

import pytest

from clang_tools import MAX_VERSION, MIN_VERSION, util

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


class FakeResponse(io.BytesIO):
    """The part of :class:`http.client.HTTPResponse` that the package uses.

    :param data: The response body.
    :param status: The HTTP status code.
    :param length: The advertised ``Content-Length`` (defaults to ``len(data)``).
    """

    def __init__(self, data: bytes, status: int = 200, length: int | None = None):
        super().__init__(data)
        self.status = status
        self.length = len(data) if length is None else length


class FakeRelease:
    """An in-memory stand-in for the static binaries' GitHub release."""

    def __init__(self) -> None:
        #: Every ``(url, timeout)`` passed to ``urlopen``, in order.
        self.requests: list[tuple[str, float | None]] = []
        #: Replaces the generated ``SHA512SUMS`` content when not `None`.
        self.sha512sums: str | None = None
        self._served: dict[str, tuple[bytes, int, int | None]] = {}

    @staticmethod
    def published(name: str) -> bytes:
        """The content of the asset *name*, as listed in ``SHA512SUMS``."""
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
        return [url.rsplit("/", 1)[-1] for url, _ in self.requests]

    def urlopen(self, url: str, timeout: float | None = None) -> FakeResponse:
        """Answer like ``urllib.request.urlopen`` would for a release URL."""
        self.requests.append((url, timeout))
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"unknown url type: {url!r}")
        if "/releases/download/" not in url:
            raise AssertionError(f"unexpected network access in a test: {url}")
        name = url.rsplit("/", 1)[-1]
        if name in self._served:
            data, status, length = self._served[name]
        elif name == "SHA512SUMS":
            data, status, length = self._sha512sums().encode(), 200, None
        elif name in RELEASE_ASSETS:
            data, status, length = self.published(name), 200, None
        else:
            data, status, length = b"Not Found", 404, None
        if status >= 400:  # like urllib's default error handling
            raise HTTPError(url, status, "Error", {}, None)
        return FakeResponse(data, status, length)

    def _sha512sums(self) -> str:
        if self.sha512sums is None:
            self.sha512sums = "".join(
                f"{hashlib.sha512(self.published(name)).hexdigest()}  {name}\n"
                for name in sorted(RELEASE_ASSETS)
            )
        return self.sha512sums


@pytest.fixture(autouse=True)
def fake_release(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRelease]:
    """Serve release downloads from memory instead of the network."""
    release = FakeRelease()
    monkeypatch.setattr(urllib.request, "urlopen", release.urlopen)
    util._fetch_sha512sums.cache_clear()
    yield release
    util._fetch_sha512sums.cache_clear()
