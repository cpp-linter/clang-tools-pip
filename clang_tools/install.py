import os
import shutil
import string
import subprocess
import sys
from posixpath import basename

from clang_tools import install_os
from clang_tools.util import check_install_os
from clang_tools.util import download_file


def clang_format_exist(version) -> bool:
    if version:
        command = [f'clang-format-{version}', '--version']
    else:
        command = ['clang-format', '--version']
    try:
        subprocess.run(command, stdout=subprocess.PIPE).returncode
        exist = True
    except FileNotFoundError:
        exist = False
    return exist


def clang_tidy_exist(version) -> bool:
    if version:
        command = [f'clang-tidy-{version}', '--version']
    else:
        command = ['clang-tidy', '--version']
    try:
        subprocess.run(command, stdout=subprocess.PIPE).returncode
        exist = True
    except FileNotFoundError:
        exist = False
    return exist


def clang_tools_binary_url(tool, version) -> string:
    base_url = "https://github.com/muttleyxd/clang-tools-static-binaries/releases/download/master-208096c1"
    if install_os == "windows":
        download_url = f"{base_url}/{tool}-{version}_{install_os}-amd64.exe".replace(" ", "")
    else:
        download_url = f"{base_url}/{tool}-{version}_{install_os}-amd64".replace(" ", "")
    return download_url


def install_clang_format(version, directory) -> None:
    if clang_format_exist(version):
        return
    clang_format_bin_url = clang_tools_binary_url("clang-format", version)
    clang_format_bin = basename(clang_format_bin_url)
    download_file(clang_format_bin_url, clang_format_bin)
    if install_os == "windows":
        new_clang_format_bin = f"clang-format-{version}.exe"
    else:
        new_clang_format_bin = f"clang-format-{version}"
    move_and_chmod_bin(clang_format_bin, new_clang_format_bin, directory)


def install_clang_tidy(version, directory) -> None:
    if clang_tidy_exist(version):
        return
    clang_tidy_bin_url = clang_tools_binary_url("clang-tidy", version)
    clang_tidy_bin = basename(clang_tidy_bin_url)
    download_file(clang_tidy_bin_url, clang_tidy_bin)
    if install_os == "windows":
        new_clang_tidy_bin = f"clang-tidy-{version}.exe"
    else:
        new_clang_tidy_bin = f"clang-tidy-{version}"
    move_and_chmod_bin(clang_tidy_bin, new_clang_tidy_bin, directory)


def move_and_chmod_bin(old_bin_name, new_bin_name, directory) -> None:
    """Move download clang-tools binary and move to bin dir with right permission."""
    if directory:
        install_dir = directory
    else:
        install_os = check_install_os()
        if install_os == "linux":
            install_dir = os.path.expanduser('~/.local/bin/')
        else:
            install_dir = os.path.dirname(sys.executable)
    try:
        if not os.path.isdir(install_dir):
            os.makedirs(install_dir)
        shutil.move(old_bin_name, f"{install_dir}/{new_bin_name}")
        os.chmod(os.path.join(install_dir, new_bin_name), 0o755)
    except PermissionError:
        raise SystemExit(
            f"Don't have permission to install {new_bin_name} to {install_dir}."
            + " Try to run with the appropriate permissions."
        )


def install_clang_tools(version, directory) -> None:
    install_clang_format(version, directory)
    install_clang_tidy(version, directory)
