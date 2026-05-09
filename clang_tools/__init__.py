"""The clang-tools package's base module."""

import os
from .util import check_install_arch, check_install_os


RESET_COLOR = "\033[0m"
YELLOW = "\033[93m"
install_os = check_install_os()
install_arch = check_install_arch()
suffix = ".exe" if install_os == "windows" else ""

binary_repo = os.getenv(
    "CLANG_TOOLS_REPO", "https://github.com/cpp-linter/clang-tools-static-binaries"
)
binary_tag = os.getenv("CLANG_TOOLS_TAG", "master-63858060")

#: The minimum major version supported by the static binary builds.
MIN_VERSION = 11
#: The maximum major version supported by the static binary builds.
MAX_VERSION = 22
