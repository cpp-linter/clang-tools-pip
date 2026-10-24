"""The clang-tools package's base module."""

import os

from .util import check_install_arch, check_install_os

RESET_COLOR = "\033[0m"
YELLOW = "\033[93m"
install_os = check_install_os()
install_arch = check_install_arch()
suffix = ".exe" if install_os == "windows" else ""

#: The index of the static binaries: every released version, with each
#: binary's download URL and SHA512 checksum.
index_url = os.getenv(
    "CLANG_TOOLS_INDEX_URL",
    "https://cpp-linter.github.io/clang-tools-static-binaries/index.json",
)
#: Set ``CLANG_TOOLS_TAG`` to download every binary from one release of
#: ``CLANG_TOOLS_REPO`` (a mirror or an older release) instead of the index.
binary_repo = os.getenv(
    "CLANG_TOOLS_REPO", "https://github.com/cpp-linter/clang-tools-static-binaries"
)
binary_tag = os.getenv("CLANG_TOOLS_TAG", "")
#: The package index that wheels are installed from when there is no static binary.
#: It is a simple repository API (PEP 503 or PEP 691) such as
#: ``https://pypi.org/simple``: ``CLANG_TOOLS_PYPI_URL``, else the index that uv or
#: pip is told to use with ``UV_DEFAULT_INDEX``, ``UV_INDEX_URL`` or
#: ``PIP_INDEX_URL``. The URL may hold a user name and password.
pypi_url = next(
    (
        url
        for url in map(
            os.getenv,
            (
                "CLANG_TOOLS_PYPI_URL",
                "UV_DEFAULT_INDEX",
                "UV_INDEX_URL",
                "PIP_INDEX_URL",
            ),
        )
        if url
    ),
    "https://pypi.org/simple",
).rstrip("/")

#: The minimum major version in a release picked with ``CLANG_TOOLS_TAG``.
MIN_VERSION = 12
#: The maximum major version in a release picked with ``CLANG_TOOLS_TAG``.
MAX_VERSION = 23
