"""
``clang_tools.install``
-----------------------

The module that performs the installation of clang-tools.
"""
import os
from pathlib import Path, PurePath
import re
import shutil
import subprocess
import sys
from typing import Optional

from . import install_os, RESET_COLOR, suffix, YELLOW
from .util import download_file, verify_sha512, get_sha_checksum


#: This pattern is designed to match only the major version number.
RE_PARSE_VERSION = re.compile(rb"version\s([\d\.]+)", re.MULTILINE)


def is_installed(tool_name: str, version: str) -> Optional[Path]:
    """Detect if the specified tool is installed.

    :param tool_name: The name of the specified tool.
    :param version: The specific version to expect.

    :returns: The path to the detected tool (if found), otherwise `None`.
    """
    version_tuple = version.split(".")
    ver_major = version_tuple[0]
    if len(version_tuple) < 3:
        # append minor and patch version numbers if not specified
        version_tuple += ("0",) * (3 - len(version_tuple))
    exe_name = (
        f"{tool_name}" + (f"-{ver_major}" if install_os != "windows" else "") + suffix
    )
    try:
        result = subprocess.run(
            [exe_name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None  # tool is not installed
    ver_num = RE_PARSE_VERSION.search(result.stdout)
    print(
        f"Found a installed version of {tool_name}:",
        ver_num.groups(0)[0].decode(encoding="utf-8"),
        end=" "
    )
    path = shutil.which(exe_name)  # find the installed binary
    if path is None:
        print()  # print end-of-line
        return None  # failed to locate the binary
    path = Path(path).resolve()
    print("at", str(path))
    if (
        ver_num is None
        or ver_num.groups(0)[0].decode(encoding="utf-8").split(".") != version_tuple
    ):
        return None  # version is unknown or not the desired major release
    return path


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


def install_tool(
    tool_name: str, version: str, directory: str, no_progress_bar: bool
) -> bool:
    """An abstract function that can install either clang-tidy or clang-format.

    :param tool_name: The name of the clang-tool to install.
    :param version: The version of the tools to install.
    :param directory: The installation directory.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :returns: `True` if the binary had to be downloaded and installed.
        `False` if the binary was not downloaded but is installed in ``directory``.
    """
    destination = Path(directory, f"{tool_name}-{version}{suffix}")
    bin_url = clang_tools_binary_url(tool_name, version)
    if destination.exists():
        print(f"{tool_name}-{version}", "already installed...")
        print("   checking SHA512...", end=" ")
        if verify_sha512(get_sha_checksum(bin_url), destination.read_bytes()):
            print("valid")
            return False
        print("invalid")
        uninstall_tool(tool_name, version, directory)
    print("downloading", tool_name, f"(version {version})")
    bin_name = str(PurePath(bin_url).stem)
    if download_file(bin_url, bin_name, no_progress_bar) is None:
        raise OSError(f"Failed to download {bin_name} from {bin_url}")
    move_and_chmod_bin(bin_name, f"{tool_name}-{version}{suffix}", directory)
    if not verify_sha512(get_sha_checksum(bin_url), destination.read_bytes()):
        raise ValueError(
            f"file was corrupted during download from {bin_url}"
        )  # pragma: no cover
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
    except PermissionError as exc:  # pragma: no cover
        raise SystemExit(
            f"Don't have permission to install {new_bin_name} to {install_dir}."
            + " Try to run with the appropriate permissions."
        ) from exc


def create_sym_link(
    tool_name: str,
    version: str,
    install_dir: str,
    overwrite: bool = False,
    target: Path = None,
) -> bool:
    """Create a symlink to the installed binary that
    doesn't have the version number appended.

    :param tool_name: The name of the clang-tool to symlink.
    :param version: The version of the clang-tool to symlink.
    :param install_dir: The installation directory to create the symlink in.
    :param overwrite: A flag to indicate if an existing symlink should be overwritten.
    :param target: The target executable's path and name for which to create a symlink
        to. If this argument is not specified (or is `None`), then the target's path and
        name is constructed from the ``tool_name``, ``version``, and ``install_dir``
        parameters.

    :returns: A `bool` describing if the symlink was created.
    """
    link_root_path = Path(install_dir)
    if not link_root_path.exists():
        link_root_path.mkdir(parents=True)
    link = link_root_path / (tool_name + suffix)
    if target is None:
        target = link_root_path / f"{tool_name}-{version}{suffix}"
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
        link.unlink()
        print("overwriting symbolic link", str(link))
    assert target.exists()
    try:
        link.symlink_to(target)
        print("symbolic link created", str(link))
        return True
    except OSError as exc:  # pragma: no cover
        print(
            "Encountered an error when trying to create the symbolic link:",
            "; ".join([x for x in exc.args if isinstance(x, str)]),
            sep="\n    ",
        )
        if install_os == "windows":
            print("Enable developer mode to create symbolic links")
        return False


def uninstall_tool(tool_name: str, version: str, directory: str):
    """Remove a specified tool of a given version.

    :param tool_name: The name of the clang tool to uninstall.
    :param version: The version of the clang-tools to remove.
    :param directory: The directory from which to remove the
        installed clang-tools.
    """
    tool_path = Path(directory, f"{tool_name}-{version}{suffix}")
    if tool_path.exists():
        print("Removing", tool_path.name, "from", str(tool_path.parent))
        tool_path.unlink()

    # check for a dead symlink
    symlink = Path(directory, f"{tool_name}{suffix}")
    if symlink.is_symlink() and not symlink.exists():
        print("Removing dead symbolic link", str(symlink))
        symlink.unlink()


def uninstall_clang_tools(version: str, directory: str):
    """Uninstall a clang tool of a given version.

    :param version: The version of the clang-tools to remove.
    :param directory: The directory from which to remove the
        installed clang-tools.
    """
    install_dir = install_dir_name(directory)
    print(f"Uninstalling version {version} from {str(install_dir)}")
    for tool in ("clang-format", "clang-tidy"):
        uninstall_tool(tool, version, install_dir)


def install_clang_tools(
    version: str, directory: str, overwrite: bool, no_progress_bar: bool
) -> None:
    """Wraps functions used to individually install tools.

    :param version: The version of the tools to install.
    :param directory: The installation directory.
    :param overwrite: A flag to indicate if the creation of a symlink has
        permission to overwrite an existing symlink.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.
    """
    install_dir = install_dir_name(directory)
    if install_dir.rstrip(os.sep) not in os.environ.get("PATH"):
        print(
            f"{YELLOW}{install_dir}",
            f"directory is not in your environment variable PATH.{RESET_COLOR}",
        )
    for tool_name in ("clang-format", "clang-tidy"):
        native_bin = is_installed(tool_name, version)
        if native_bin is None:  # (not already installed)
            # `install_tool()` guarantees that the binary exists now
            install_tool(tool_name, version, install_dir, no_progress_bar)
        create_sym_link(  # pragma: no cover
            tool_name, version, install_dir, overwrite, native_bin
        )
