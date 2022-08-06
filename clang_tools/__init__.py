"""The clang-tools package's base module."""
from .util import check_install_os


install_os = check_install_os()
suffix = ".exe" if install_os == "windows" else ""