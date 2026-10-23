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
#: The base URL of the PyPI JSON API, used to install wheels when there is no
#: static binary. Set ``CLANG_TOOLS_PYPI_URL`` to use a mirror.
pypi_url = os.getenv("CLANG_TOOLS_PYPI_URL", "https://pypi.org/pypi").rstrip("/")

#: The minimum major version in a release picked with ``CLANG_TOOLS_TAG``.
MIN_VERSION = 12
#: The maximum major version in a release picked with ``CLANG_TOOLS_TAG``.
MAX_VERSION = 23
