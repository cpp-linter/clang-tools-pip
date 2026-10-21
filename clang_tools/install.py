"""
``clang_tools.install``
-----------------------

The module that performs the installation of clang-tools.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePath
from typing import cast

from . import (
    MAX_VERSION,
    MIN_VERSION,
    RESET_COLOR,
    YELLOW,
    binary_repo,
    binary_tag,
    index_url,
    install_arch,
    install_os,
    suffix,
)
from .util import (
    PyPIFallback,
    Version,
    download_file,
    fetch_index,
    get_sha_checksum,
    verify_sha512,
)

#: This pattern is designed to match only the major version number.
RE_PARSE_VERSION = re.compile(rb"version\s([\d\.]+)", re.MULTILINE)
#: A binary's file name: no path separators, and not ``.`` or ``..``.
RE_FILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def is_installed(tool_name: str, version: Version) -> Path | None:
    """Detect if the specified tool is installed.

    :param tool_name: The name of the specified tool.
    :param version: The specific major version to expect.

    :returns: The path to the detected tool (if found), otherwise `None`.
    """
    exe_name = (
        f"{tool_name}"
        + (f"-{version.info[0]}" if install_os != "windows" else "")
        + suffix
    )
    try:
        result = subprocess.run(
            [exe_name, "--version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None  # tool is not installed
    ver_num = RE_PARSE_VERSION.search(result.stdout)
    assert ver_num is not None, "Failed to parse version from tool output"
    ver_match = cast(bytes, ver_num.groups(0)[0]).decode(encoding="utf-8")
    print(
        f"Found a installed version of {tool_name}:",
        ver_match,
        end=" ",
    )
    exe_path = shutil.which(exe_name)  # find the installed binary
    if exe_path is None:
        print()  # print end-of-line
        return None  # failed to locate the binary
    path = Path(exe_path).resolve()
    print("at", str(path))
    ver_tuple = ver_match.split(".")
    if ver_tuple is None or ver_tuple[0] != str(version.info[0]):
        return None  # version is unknown or not the desired major release
    return path


def platform_name() -> str:
    """The platform name used in the static binaries' file names."""
    os_name = "macos" if install_os == "macosx" else install_os
    return f"{os_name}-{install_arch}"


def available_versions() -> list[int]:
    """The major versions that can be installed as static binaries."""
    if binary_tag:
        return list(range(MIN_VERSION, MAX_VERSION + 1))
    return sorted(int(v) for v in fetch_index(index_url)["versions"])


def find_binary(tool: str, version: str) -> tuple[str, str]:
    """Find where to download a binary and the checksum it must match.

    :param tool: The name of the tool to download.
    :param version: The version of the tool to download.

    :returns: The download URL and the expected SHA512 checksum.
    :raises PyPIFallback: If the binary is not available.
    """
    if binary_tag:
        url = clang_tools_binary_url(tool, version)
        return url, get_sha_checksum(url)
    major = version.split(".", 1)[0]
    entry = fetch_index(index_url)["versions"].get(major)
    if entry is None:
        raise PyPIFallback(
            f"{major} is not available in static binary builds. "
            f"Available versions: {', '.join(map(str, available_versions()))}."
        )
    binary = entry["tools"].get(tool, {}).get(platform_name())
    if binary is None:
        raise PyPIFallback(
            f"{tool} {major} is not available in static binary builds"
            f" for {platform_name()}."
        )
    return binary["url"], binary["sha512"]


def clang_tools_binary_url(tool: str, version: str) -> str:
    """The download URL of a binary.

    :param tool: The name of the tool to download.
    :param version: The version of the tool to download.

    :returns: The URL used to download the specified tool.
    """
    if not binary_tag:
        return find_binary(tool, version)[0]
    base_url = f"{binary_repo}/releases/download/{binary_tag}"
    download_url = f"{base_url}/{tool}-{version}_{platform_name()}{suffix}"
    return download_url.replace(" ", "")


def binary_file_name(tool_name: str, version: str) -> str:
    """The file name of an installed binary, such as ``clang-format-21``.

    :param tool_name: The name of the tool.
    :param version: The version of the tool.

    :returns: The file name, which never points outside the install directory.
    """
    file_name = f"{tool_name}-{version}{suffix}"
    if not RE_FILE_NAME.fullmatch(file_name):
        raise ValueError(f"Invalid tool name or version: {tool_name!r} {version!r}")
    return file_name


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
    :raises PyPIFallback: If the binary is not available or could not be downloaded.
    """
    try:
        file_name = binary_file_name(tool_name, version)
    except ValueError as exc:  # no static binary has such a name
        raise PyPIFallback(str(exc)) from exc
    destination = Path(directory, file_name)
    bin_url, checksum = find_binary(tool_name, version)
    if destination.exists():
        print(f"{tool_name}-{version}", "already installed...")
        print("   checking SHA512...", end=" ")
        if verify_sha512(checksum, destination.read_bytes()):
            print("valid")
            return False
        print("invalid")
        uninstall_tool(tool_name, version, directory)
    print("Downloading", tool_name, f"(version {version})")
    bin_name = str(PurePath(bin_url).stem)
    # Download to a private directory and verify the file before installing it.
    with tempfile.TemporaryDirectory() as download_dir:
        downloaded = Path(download_dir, bin_name)
        download_file(bin_url, str(downloaded), no_progress_bar)
        if not verify_sha512(checksum, downloaded.read_bytes()):
            raise PyPIFallback(f"File was corrupted during download from {bin_url}")
        move_and_chmod_bin(str(downloaded), file_name, directory)
    return True


def default_install_dir() -> str:
    """The install directory used when none is given (in resolved form).

    :returns: ``~/.local/bin`` on Linux, otherwise the directory that holds the
        Python executable (the ``bin`` or ``Scripts`` directory of a virtual
        environment).
    """
    if install_os == "linux":
        return os.path.realpath(os.path.expanduser("~/.local/bin"))
    return os.path.realpath(os.path.dirname(sys.executable))


def install_dir_name(directory: str) -> str:
    """Automate directory choosing if not explicitly specified by user.

    :param directory: The directory that was manually specified in the CLI. If this was
        not specified, then default values are used depending on the operating system.
        If this path exists but is not a directory, a warning is shown and the default
        directory is used instead.

    :returns: The install directory name, with symbolic links resolved. Use only this
        resolved path afterwards, so the files are always changed where the messages
        say.
    """
    if directory:
        resolved = os.path.realpath(directory)
        if os.path.isdir(resolved) or not os.path.exists(resolved):
            return resolved
        print(
            f"{YELLOW}{resolved} is not a directory.",
            f"Using the default directory instead.{RESET_COLOR}",
            file=sys.stderr,
        )
    return default_install_dir()


def create_install_dir(install_dir: str) -> None:
    """Create the install directory if it does not exist yet.

    Missing parent directories (such as ``~/.local``) are only created for the
    default directory. Any other directory must be in an existing directory, so a
    mistyped ``--directory`` value fails instead of creating a tree of directories.

    :param install_dir: The install directory, as returned by `install_dir_name()`.
    """
    path = Path(install_dir)
    try:
        path.mkdir(parents=install_dir == default_install_dir(), exist_ok=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"Can't create the install directory {install_dir}"
            f" because {path.parent} does not exist."
        ) from exc
    except OSError as exc:
        raise SystemExit(
            f"Can't create the install directory {install_dir}: {exc.strerror or exc}"
        ) from exc


def is_in_path(directory: str) -> bool:
    """Check if a directory is listed in the ``PATH`` environment variable.

    :param directory: The directory to look for (in resolved form).

    :returns: `True` if an entry of ``PATH`` resolves to ``directory``.
    """
    wanted = os.path.normcase(directory)
    return any(
        os.path.normcase(os.path.realpath(entry)) == wanted
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry
    )


def move_and_chmod_bin(old_bin_name: str, new_bin_name: str, install_dir: str) -> None:
    """Move download clang-tools binary and move to bin dir with right permission.

    :param old_bin_name: The downloaded file's name.
    :param new_bin_name: The desired name of the file after being moved to
        the ``install_dir``.
    :param install_dir: The target installation directory. It must exist.
    """
    print("Installing", new_bin_name, "to", install_dir)
    try:
        shutil.move(old_bin_name, f"{install_dir}/{new_bin_name}")
        os.chmod(os.path.join(install_dir, new_bin_name), 0o755)
    except PermissionError as exc:
        raise SystemExit(
            f"Don't have permission to install {new_bin_name} to {install_dir}."
            + " Try to run with the appropriate permissions."
        ) from exc


def create_sym_link(
    tool_name: str,
    version: str,
    install_dir: str,
    overwrite: bool = False,
    target: Path | None = None,
) -> bool:
    """Create a symlink to the installed binary that
    doesn't have the version number appended.

    :param tool_name: The name of the clang-tool to symlink.
    :param version: The version of the clang-tool to symlink.
    :param install_dir: The installation directory to create the symlink in. It must
        exist.
    :param overwrite: A flag to indicate if an existing symlink should be overwritten.
    :param target: The target executable's path and name for which to create a symlink
        to. If this argument is not specified (or is `None`), then the target's path and
        name is constructed from the ``tool_name``, ``version``, and ``install_dir``
        parameters.

    :returns: A `bool` describing if the symlink was created.
    """
    link_root_path = Path(install_dir)
    link = link_root_path / (tool_name + suffix)
    if target is None:
        target = link_root_path / f"{tool_name}-{version}{suffix}"
    if os.path.lexists(link):  # also true for a link whose target is gone
        if not link.is_symlink():
            print(
                "File",
                str(link),
                "already exists and it is not a symbolic link. Leaving it as is.",
            )
            return False
        if not overwrite:
            print(
                "Symbolic link",
                str(link),
                "already exists. Use '-f' to overwrite. Leaving it as is.",
            )
            return False
        link.unlink()
        print("Overwriting symbolic link", str(link))
    assert target.exists()
    try:
        link.symlink_to(target)
        print("Symbolic link created", str(link))
        return True
    except OSError as exc:
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
    tool_path = Path(directory, binary_file_name(tool_name, version))
    if tool_path.exists():
        print("Removing", tool_path.name, "from", str(tool_path.parent))
        tool_path.unlink()

    # check for a dead symlink
    symlink = Path(directory, f"{tool_name}{suffix}")
    if symlink.is_symlink() and not symlink.exists():
        print("Removing dead symbolic link", str(symlink))
        symlink.unlink()


def uninstall_clang_tools(tools: list[str], version: str, directory: str):
    """Uninstall a clang tool of a given version.

    :param tools: The list of tool names to uninstall.
    :param version: The version of the clang-tools to remove.
    :param directory: The directory from which to remove the
        installed clang-tools.
    """
    install_dir = install_dir_name(directory)
    print(f"Uninstalling version {version} from {install_dir!s}")
    for tool in tools:
        uninstall_tool(tool, version, install_dir)


def install_clang_tools(
    version: Version,
    tools: list[str],
    directory: str,
    overwrite: bool,
    no_progress_bar: bool,
) -> None:
    """Wraps functions used to individually install tools.

    :param version: The version of the tools to install.
    :param tools: The specify tool(s) to install.
    :param directory: The installation directory.
    :param overwrite: A flag to indicate if the creation of a symlink has
        permission to overwrite an existing symlink.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.
    :raises PyPIFallback: If a tool's static binary is not available or could not be
        downloaded, so the wheel should be tried instead.
    """
    install_dir = install_dir_name(directory)
    create_install_dir(install_dir)
    if not is_in_path(install_dir):
        print(
            f"{YELLOW}{install_dir}",
            f"directory is not in your environment variable PATH.{RESET_COLOR}",
        )
    for tool_name in tools:
        native_bin = is_installed(tool_name, version)
        if native_bin is None:  # (not already installed)
            # only a download needs the list of available versions
            versions = available_versions()
            if version.info[0] not in versions:
                raise PyPIFallback(
                    f"{version.info[0]} is not available in static binary builds. "
                    f"Available versions: {', '.join(map(str, versions))}."
                )
            # `install_tool()` guarantees that the binary exists now
            install_tool(tool_name, version.string, install_dir, no_progress_bar)
        create_sym_link(tool_name, version.string, install_dir, overwrite, native_bin)
