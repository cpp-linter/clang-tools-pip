import string
import subprocess
import shutil
import os
from posixpath import basename
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
    install_os = check_install_os()
    base_url = "https://github.com/muttleyxd/clang-tools-static-binaries/releases/download/master-208096c1"
    if install_os == "windows":
        download_url = f"{base_url}/{tool}-{version}_{install_os}-amd64.exe".replace(" ", "")
    else:
        download_url = f"{base_url}/{tool}-{version}_{install_os}-amd64".replace(" ", "")
    return download_url


def install_clang_format(version, directory) -> None:
    if clang_format_exist(version):
        return
    clang_format_binary_url = clang_tools_binary_url("clang-format", version)
    clang_format_binary = basename(clang_format_binary_url)
    download_file(clang_format_binary_url, clang_format_binary)
    move_and_chmod_binary(clang_format_binary, f"clang-format-{version}", directory)


def install_clang_tidy(version, directory) -> None:
    if clang_tidy_exist(version):
        return
    clang_tidy_binary_url = clang_tools_binary_url("clang-tidy", version)
    clang_tidy_binary = basename(clang_tidy_binary_url)
    download_file(clang_tidy_binary_url, clang_tidy_binary)
    move_and_chmod_binary(clang_tidy_binary, f"clang-tidy-{version}", directory)


def move_and_chmod_binary(old_file_name, new_file_name, directory) -> None:
    """Move download clang-tools binary and move to bin dir with right permission."""
    if directory:
        clang_tools_dir = directory
    else:
        install_os = check_install_os()
        if install_os in ['linux', 'macosx']:
            clang_tools_dir = "/usr/bin"
        elif install_os == "windows":
            clang_tools_dir = "C:/bin"
        else:
            raise Exception(f"Not support {install_os}")
    shutil.move(old_file_name, f"{clang_tools_dir}/{new_file_name}")
    os.chmod(os.path.join(clang_tools_dir, new_file_name), 0o777)


def install_clang_tools(version, directory) -> None:
    install_clang_format(version, directory)
    install_clang_tidy(version, directory)
