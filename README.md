# clang-tools

[![PyPI](https://img.shields.io/pypi/v/clang-tools)](https://pypi.org/project/clang-tools/) [![Python test](https://github.com/shenxianpeng/clang-tools-pip/actions/workflows/python-test.yml/badge.svg)](https://github.com/shenxianpeng/clang-tools-pip/actions/workflows/python-test.yml) [![codecov](https://codecov.io/gh/shenxianpeng/clang-tools-pip/branch/master/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/shenxianpeng/clang-tools-pip) [![Platfrom](https://img.shields.io/badge/platform-linux--64%20%7C%20win--64%20%7C%20osx--64%20-blue)](https://pypi.org/project/clang-tools/)

Install clang-tools binaries (clang-format, clang-tidy) with pip.

## Install

Install `clang-tools` command with pip

```bash
$ sudo pip install clang-tools
```

## Usage

```bash
$ sudo clang-tools --help
usage: clang-tools [-h] [-i INSTALL] [-d DIRECTORY]

optional arguments:
  -h, --help            show this help message and exit
  -i INSTALL, --install INSTALL
                        Install clang-tools with specific version. default is 12.
  -d DIRECTORY, --directory DIRECTORY
                        The directory where is the clang-tools install.
```
Use `clang-tools` command to install version 13 binaries.

```bash
$ sudo clang-tools --install 13
# Or install to a specified directory
$ sudo clang-tools --install 13 --directory .

$ clang-format-13 --version
clang-format version 13.0.0

$ clang-tidy-13 --version
LLVM (http://llvm.org/):
  LLVM version 13.0.0
  Optimized build.
  Default target: x86_64-unknown-linux-gnu
  Host CPU: skylake
```
