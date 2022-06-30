import string
import subprocess
import urllib.request
import platform


def check_install_os() -> string:
    os = platform.system().lower()
    if os == "darwin":
        os = "macosx"
    return os


def download_file(url, file_name) -> None:
    urllib.request.urlretrieve(url, file_name)


def unpack_file(file_name) -> int:
    command = ["tar", "-xvf", file_name]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    return result.returncode


def cmake_and_build():
    command = [
        "cmake",
        "-S" "llvm-project-12.0.1.src/llvm",
        "-B", "llvm-project-12.0.1.src/build",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DLLVM_ENABLE_PROJECTS=\"clang;clang-tools-extra\"",
        "-DLLVM_BUILD_STATIC=ON",
        "-DCMAKE_CXX_FLAGS=\"-s -flto\"",
        "-DCMAKE_BUILD_TYPE=MinSizeRel",
        "-DCMAKE_CXX_COMPILER=g++-10",
        "-DCMAKE_C_COMPILER=gcc-10",
        ]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    print(result.stdout.decode("utf-8"))
