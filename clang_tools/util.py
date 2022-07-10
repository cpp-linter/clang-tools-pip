import platform
import string
import subprocess
import urllib.request


def check_install_os() -> string:
    os = platform.system().lower()
    if os == "darwin":
        os = "macosx"
    if os not in ['linux', 'macosx', 'windows']:
        raise SystemExit(f"Not support {os}")
    return os


def download_file(url, file_name) -> string:
    try:
        file, _ = urllib.request.urlretrieve(url, file_name)
    except ValueError:
        return None
    return file


def unpack_file(file_name) -> int:
    command = ["tar", "-xvf", file_name]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    return result.returncode
