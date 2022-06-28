import string
import subprocess
import shutil
import os
from posixpath import basename
from clang_tools.util import check_os
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

def clang_tools_binary_url(tool, version, os) -> string:
    return f"https://github.com/muttleyxd/clang-tools-static-binaries/releases/download/master-208096c1/{tool}-{version}_{os}-amd64"

def install_clang_format(version) -> None:
    if clang_format_exist(version):
        return
    clang_format_binary_url = clang_tools_binary_url("clang-format", version, os)
    clang_format_binary = basename(clang_format_binary_url)
    download_file(clang_format_binary_url, clang_format_binary)
    install_clang_binary(clang_format_binary, f"clang-format-{version}")

def install_clang_tidy(version) -> None:
    if clang_tidy_exist(version):
        return
    clang_tidy_binary_url = clang_tools_binary_url("clang-tidy", version, os)
    clang_tidy_binary = basename(clang_tidy_binary_url)
    download_file(clang_tidy_binary_url, clang_tidy_binary)
    install_clang_binary(clang_tidy_binary, f"clang-tidy-{version}")

def install_clang_binary(old_file_name, new_file_name) -> None:
    """Move download clang-tools binary and move to bin dir with right permission."""
    os = check_os()
    if os in ['linux', 'macosx']:
        clang_tools_dir = "/usr/bin"
    elif os == "windows":
        clang_tools_dir = "C:/bin"
    else:
        raise Exception(f"Not support {os}")
    shutil.move(old_file_name, f"{clang_tools_dir}/{new_file_name}")
    os.chmod(f"{clang_tools_dir}/{new_file_name}", "0777")
    
def install_clang_tools(version) -> None:
    install_clang_format(version)
    install_clang_tidy(version)
