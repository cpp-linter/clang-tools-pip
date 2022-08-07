"""
``clang_tools.install``
-----------------------

The module that performs the installation of clang-tools.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from pathlib import PurePath

from . import install_os
from . import RESET_COLOR
from . import suffix
from . import YELLOW
from .util import download_file

# pylint: disable=fixme


def is_installed(tool_name: str, version: str) -> bool:
    """An abstract functions to check if a specified clang tool is installed.

    :param tool_name: The name of the tool.
    :param version: The version of the tool to look for. If provided a blank string,
        then only the ``tool_name`` is executed during the check.
    :returns: A `bool` describing if the tool was installed and executed properly.
    """
    command = [tool_name, "--version"]
    if version:
        command[0] += f"-{version}"
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def clang_tools_binary_url(
    tool: str, version: str, release_tag: str = "master-208096c1"
) -> str:
    """Assemble the URL to the binary.

    :param tool: The name of the tool to download.
    :param version: The version of the tool to download.
    :param release_tag: The release tag used in the base URL.

    :returns: The URL used to download the specified tool.
    """
    base_url = (
        "https://github.com/muttleyxd/clang-tools-static-binaries/releases/download/"
        + release_tag
    )
    download_url = f"{base_url}/{tool}-{version}_{install_os}-amd64{suffix}"
    return download_url.replace(" ", "")


def install_tool(tool_name: str, version: str, directory: str) -> bool:
    """An abstract function that can install either clang-tidy or clang-format."""
    if is_installed(tool_name, version):
        # TODO should probably skip this if `directory` is not in the PATH env var.
        print(f"{tool_name}-{version}", "already installed")
        return False
    bin_url = clang_tools_binary_url(tool_name, version)
    bin_name = str(PurePath(bin_url).stem)
    print("downloading", tool_name, f"(version {version})")
    download_file(bin_url, bin_name)
    move_and_chmod_bin(bin_name, f"{tool_name}-{version}{suffix}", directory)
    return True


def install_dir_name(directory: str) -> str:
    """Automate directory choosing if not explicitly specified by user.

    :param directory: The directory that was manually specified in the CLI. If this was
        not specified, then default values are used depending on the operating system.

    :returns: The install directory name (in absolute form).
    """
    if directory:
        return os.path.abspath(directory)
    if install_os == "linux":
        return os.path.expanduser("~/.local/bin/")
    # if install_os == "windows":
    #     # C:\Users\{username}\AppData\Local\clang-tools
    #     return os.path.join(os.getenv("LOCALAPPDATA"), "clang-tools")
    return os.path.dirname(sys.executable)


def move_and_chmod_bin(old_bin_name: str, new_bin_name: str, install_dir: str) -> None:
    """Move download clang-tools binary and move to bin dir with right permission.

    :param old_bin_name: The downloaded file's name.
    :param new_bin_name: The desired name of the file after being moved to
        the ``install_dir``.
    :param install_dir: The target installation directory.
    """
    print("Installing", new_bin_name, "to", install_dir)
    try:
        if not os.path.isdir(install_dir):
            os.makedirs(install_dir)
        shutil.move(old_bin_name, f"{install_dir}/{new_bin_name}")
        os.chmod(os.path.join(install_dir, new_bin_name), 0o755)
    except PermissionError as exc:
        raise SystemExit(
            f"Don't have permission to install {new_bin_name} to {install_dir}."
            + " Try to run with the appropriate permissions."
        ) from exc


def create_sym_link(
    tool_name: str, version: str, install_dir: str, overwrite: bool = False
) -> bool:
    """Create a symlink to the installed binary that
    doesn't have the version number appended.

    :param tool_name: The name of the clang-tool to symlink.
    :param version: The version of the clang-tool to symlink.
    :param install_dir: The installation directory to create the symlink in.
    :param overwrite: A flag to indicate if an existing symlink should be overwritten.

    :returns: A `bool` describing if the symlink was created.
    """
    link = Path(install_dir) / (tool_name + suffix)
    target = Path(install_dir) / f"{tool_name}-{version}{suffix}"
    if link.exists():
        if not link.is_symlink():
            print(
                "file",
                str(link),
                "already exists and it is not a symbolic link. Leaving it as is.",
            )
            return False
        if not overwrite:
            print(
                "symbolic link",
                str(link),
                "already exists. Use '-f' to overwrite. Leaving it as is.",
            )
            return False
        os.remove(str(link))
        print("overwriting symbolic link", str(link))
    link.symlink_to(target)
    print("symbolic link created", str(link))
    return True


def install_clang_tools(version: str, directory: str, overwrite: bool) -> None:
    """Wraps functions used to individually install tools.

    :param version: The version of the tools to install.
    :param directory: The installation directory.
    :param overwrite: A flag to indicate if the creation of a symlink has
        permission to overwrite an existing symlink.
    """
    install_dir = install_dir_name(directory)
    if install_dir.rstrip(os.sep) not in os.environ.get("PATH"):
        print(
            f"{YELLOW}{install_dir}",
            f"directory is not in your environment variable PATH.{RESET_COLOR}",
        )
    for tool_name in ("clang-format", "clang-tidy"):
        if install_tool(tool_name, version, install_dir):
            create_sym_link(tool_name, version, install_dir, overwrite)
