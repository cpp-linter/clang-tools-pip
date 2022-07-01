import string
import subprocess
from urllib.error import HTTPError
import urllib.request
import platform


def check_install_os() -> string:
    os = platform.system().lower()
    if os == "darwin":
        os = "macosx"
    return os


def download_file(url, file_name) -> None:
    try:
        urllib.request.urlretrieve(url, file_name)
    except HTTPError:
        raise SystemExit(f"Not found {file_name}, exit!")


def unpack_file(file_name) -> int:
    command = ["tar", "-xvf", file_name]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    return result.returncode


def cmake_and_build():
    command = []
    result = subprocess.run(command, stdout=subprocess.PIPE)
    print(result.stdout.decode("utf-8"))
