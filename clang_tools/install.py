"""
``clang_tools.install``
-----------------------

The module that performs the installation of clang-tools.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import NamedTuple, cast

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
#: A file or directory name in an archive, such as ``__stddef_max_align_t.h``.
RE_ENTRY_NAME = re.compile(r"[A-Za-z0-9_.+-]+")


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


#: The tools that parse C and C++ code. They need clang's builtin headers, such as
#: ``stddef.h``, which clang looks for in ``<bin>/../lib/clang/<version>/include``.
HEADER_TOOLS = frozenset(
    {"clang-tidy", "clang-query", "clang-include-cleaner", "clang-scan-deps"}
)


class Binary(NamedTuple):
    """Where to download a static binary from, and what it must match."""

    #: The download URL of the binary.
    url: str
    #: The SHA512 checksum of the binary.
    sha512: str
    #: The tag of the release that holds the binary.
    tag: str
    #: The download URL and SHA512 checksum of the release's clang resource headers,
    #: or `None` if the release has none.
    headers: tuple[str, str] | None


def find_binary(tool: str, version: str) -> Binary:
    """Find where to download a binary and the checksum it must match.

    :param tool: The name of the tool to download.
    :param version: The version of the tool to download.

    :returns: The binary's download URL, checksum and release.
    :raises PyPIFallback: If the binary is not available.
    """
    major = version.split(".", 1)[0]
    if binary_tag:
        url = clang_tools_binary_url(tool, version)
        base_url = url.rsplit("/", 1)[0]
        headers_url = f"{base_url}/clang-resource-headers-{major}.tar.gz"
        try:
            headers: tuple[str, str] | None = (
                headers_url,
                get_sha_checksum(headers_url),
            )
        except PyPIFallback:  # older releases have no headers
            headers = None
        return Binary(url, get_sha_checksum(url), binary_tag, headers)
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
    archive = entry.get("resource_headers")
    headers = None if archive is None else (archive["url"], archive["sha512"])
    return Binary(binary["url"], binary["sha512"], entry["tag"], headers)


def clang_tools_binary_url(tool: str, version: str) -> str:
    """The download URL of a binary.

    :param tool: The name of the tool to download.
    :param version: The version of the tool to download.

    :returns: The URL used to download the specified tool.
    """
    if not binary_tag:
        return find_binary(tool, version).url
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


def data_dir() -> Path:
    """The directory that keeps the downloaded binaries and headers (resolved).

    Set ``CLANG_TOOLS_DATA_DIR`` to use another directory. Otherwise it is
    ``$XDG_DATA_HOME/clang-tools`` (``~/.local/share/clang-tools``) on Linux,
    ``~/Library/Application Support/clang-tools`` on macOS and
    ``%LOCALAPPDATA%\\clang-tools`` on Windows.
    """
    configured = os.getenv("CLANG_TOOLS_DATA_DIR")
    if configured:
        return Path(os.path.realpath(configured))
    if install_os == "windows":
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    elif install_os == "macosx":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.getenv("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(os.path.realpath(base), "clang-tools")


def make_dir(path: Path) -> None:
    """Create a directory in the data directory, and its parents."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(
            f"Can't create {path}: {exc.strerror or exc}."
            " Set CLANG_TOOLS_DATA_DIR to a writable directory."
        ) from exc


def download_verified(
    url: str, checksum: str, destination: Path, no_progress_bar: bool
) -> bool:
    """Download a file unless ``destination`` already holds it.

    The file is downloaded next to ``destination`` and only moved there once its
    checksum matches, so ``destination`` is never a partial or corrupted file.

    :param url: The URL to download from.
    :param checksum: The SHA512 checksum that the file must match.
    :param destination: Where to put the file.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :returns: `True` if the file had to be downloaded.
    :raises PyPIFallback: If the file could not be downloaded or is corrupted.
    """
    if destination.is_file() and verify_sha512(checksum, destination.read_bytes()):
        return False
    make_dir(destination.parent)
    print("Downloading", url)
    with tempfile.TemporaryDirectory(dir=destination.parent) as download_dir:
        downloaded = Path(download_dir, destination.name)
        download_file(url, str(downloaded), no_progress_bar)
        if not verify_sha512(checksum, downloaded.read_bytes()):
            raise PyPIFallback(f"File was corrupted during download from {url}")
        downloaded.chmod(0o755)
        os.replace(downloaded, destination)
    return True


def has_headers(prefix: Path, major: str) -> bool:
    """Check if the clang resource headers of a version are in ``prefix``.

    LLVM 15 and older name the directory with the full version (``lib/clang/15.0.2``),
    later versions with the major version only (``lib/clang/16``).
    """
    clang_dir = prefix / "lib" / "clang"
    return clang_dir.is_dir() and any(
        d.name == major or d.name.startswith(f"{major}.") for d in clang_dir.iterdir()
    )


def extract_headers(archive: Path, destination: Path) -> PurePosixPath:
    """Extract the clang resource headers archive.

    Only directories and regular files under ``lib/clang/<version>/`` are accepted,
    so the archive can't write anywhere else.

    :param archive: The ``clang-resource-headers-<major>.tar.gz`` file.
    :param destination: The directory to extract into.

    :returns: The extracted ``lib/clang/<version>`` directory, relative to
        ``destination``.
    :raises PyPIFallback: If the archive has any other entry.
    """
    expected = ("lib", "clang")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        versions = set()
        for member in members:
            parts = PurePosixPath(member.name).parts
            # plain names only: no "..", and no "\\" or ":" that Windows reads as
            # a separator or a drive
            inside = parts[:2] == expected[: len(parts)] and all(
                RE_ENTRY_NAME.fullmatch(part) and part != ".." for part in parts
            )
            if not inside or not (member.isdir() or len(parts) > 3 and member.isfile()):
                raise PyPIFallback(
                    f"Unexpected entry {member.name!r} in {archive.name}"
                )
            if len(parts) > 2:
                versions.add(parts[2])
        if len(versions) != 1:
            raise PyPIFallback(f"{archive.name} must hold the headers of one version")
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(
                    cast(io.BufferedReader, tar.extractfile(member)).read()
                )
    return PurePosixPath(*expected, versions.pop())


def install_headers(
    headers: tuple[str, str], prefix: Path, major: str, no_progress_bar: bool
) -> None:
    """Install the clang resource headers of a version in ``prefix``, once.

    :param headers: The download URL and SHA512 checksum of the headers archive.
    :param prefix: The directory that holds ``bin/`` with the binaries.
    :param major: The major version of the headers.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :raises PyPIFallback: If the headers could not be downloaded or extracted.
    """
    if has_headers(prefix, major):
        return
    url, checksum = headers
    make_dir(prefix)
    with tempfile.TemporaryDirectory(dir=prefix) as work_dir:
        archive = Path(work_dir, "headers.tar.gz")
        download_verified(url, checksum, archive, no_progress_bar)
        extracted = Path(work_dir, "extracted")
        version_dir = extract_headers(archive, extracted)
        final = prefix.joinpath(*version_dir.parts)
        final.parent.mkdir(parents=True, exist_ok=True)
        try:
            # one rename, so the directory is either complete or not there
            Path(extracted, *version_dir.parts).rename(final)
        except OSError:
            if not final.is_dir():
                raise  # pragma: no cover (not a parallel install of the same version)


def link_binary(stored: Path, destination: Path) -> None:
    """Make ``destination`` run the binary ``stored`` in the data directory.

    ``destination`` becomes a symbolic link, or a copy where links can't be created
    (Windows without Developer Mode). clang looks for its resource headers in
    ``../lib/clang`` from the binary it runs. Through a link, that is next to
    ``stored`` on Linux and macOS, but next to the link on Windows (in LLVM 15 and
    older at least). So for a copy, and on Windows, the headers are also copied to
    ``<destination>/../../lib``.
    """
    copied = False
    try:
        if not (destination.is_symlink() and destination.resolve() == stored.resolve()):
            print("Installing", destination.name, "to", str(destination.parent))
            # made next to `destination` and moved there in one step, which also
            # replaces an older link or copy
            with tempfile.TemporaryDirectory(dir=destination.parent) as work_dir:
                staged = Path(work_dir, destination.name)
                try:
                    staged.symlink_to(stored)
                except OSError:
                    shutil.copy2(stored, staged)
                    copied = True
                os.replace(staged, destination)
        if copied or install_os == "windows":
            copy_headers(
                stored.parent.parent / "lib", destination.parent.parent / "lib"
            )
    except PermissionError as exc:
        raise SystemExit(
            f"Don't have permission to install {destination.name} to"
            f" {destination.parent}. Try to run with the appropriate permissions."
        ) from exc


def copy_headers(source: Path, lib: Path) -> None:
    """Copy each version of the clang resource headers in ``source`` that ``lib``
    doesn't have yet.

    :param source: The ``lib`` directory next to a stored binary's ``bin``.
    :param lib: The ``lib`` directory next to the install directory.
    """
    if not (source / "clang").is_dir():
        return
    for version_dir in (source / "clang").iterdir():
        target = lib / "clang" / version_dir.name
        if target.is_dir():
            continue
        print("Copying the clang resource headers to", str(lib))
        target.parent.mkdir(parents=True, exist_ok=True)
        # copied next to `target` and renamed, so `target` is complete or not there
        with tempfile.TemporaryDirectory(dir=target.parent) as work_dir:
            staged = Path(work_dir, version_dir.name)
            shutil.copytree(version_dir, staged)
            try:
                staged.rename(target)
            except OSError:
                if not target.is_dir():
                    raise  # pragma: no cover (not a parallel install)


def install_tool(
    tool_name: str, version: str, directory: str, no_progress_bar: bool
) -> bool:
    """Install a static binary of a clang tool.

    The binary is kept in `data_dir()`, in a directory per release, next to the clang
    resource headers that tools in `HEADER_TOOLS` need. ``directory`` gets a link to
    it, named like ``clang-tidy-21``.

    :param tool_name: The name of the clang-tool to install.
    :param version: The version of the tools to install.
    :param directory: The installation directory.
    :param no_progress_bar: A flag used to disable the downloads' progress bar.

    :returns: `True` if the binary had to be downloaded, `False` if it was already
        in the data directory.
    :raises PyPIFallback: If the binary is not available or could not be downloaded.
    """
    try:
        file_name = binary_file_name(tool_name, version)
    except ValueError as exc:  # no static binary has such a name
        raise PyPIFallback(str(exc)) from exc
    binary = find_binary(tool_name, version)
    if not RE_FILE_NAME.fullmatch(binary.tag):
        raise PyPIFallback(f"Invalid release tag {binary.tag!r}")
    major = version.split(".", 1)[0]
    prefix = data_dir() / binary.tag
    stored = prefix / "bin" / f"{tool_name}-{major}{suffix}"
    downloaded = download_verified(binary.url, binary.sha512, stored, no_progress_bar)
    if tool_name in HEADER_TOOLS:
        if binary.headers is None:
            print(
                f"{YELLOW}Release {binary.tag} has no clang resource headers, so"
                f" {tool_name} may report errors like 'stddef.h' file not found."
                f"{RESET_COLOR}",
                file=sys.stderr,
            )
        else:
            install_headers(binary.headers, prefix, major, no_progress_bar)
    link_binary(stored, Path(directory, file_name))
    return downloaded


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
    if os.path.lexists(tool_path):  # also a link whose target is gone
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


def is_managed(path: Path, install_dir: str) -> bool:
    """Check if a binary found in ``PATH`` was installed by clang-tools.

    :param path: The resolved path of the binary.
    :param install_dir: The install directory (in resolved form).

    :returns: `True` if the binary is in the data directory, or is a file in the
        install directory (as older versions of clang-tools installed them).
    """
    return path.parent == Path(install_dir) or path.is_relative_to(data_dir())


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
        if native_bin is not None and is_managed(native_bin, install_dir):
            native_bin = None  # installed by clang-tools: check it and its headers
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
