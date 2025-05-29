"""The clang-tools package's base module."""

from .util import check_install_os


RESET_COLOR = "\033[0m"
YELLOW = "\033[93m"
install_os = check_install_os()
suffix = ".exe" if install_os == "windows" else ""

# tag of https://github.com/cpp-linter/clang-tools-static-binaries/releases
release_tag = "master-b35c5633"
