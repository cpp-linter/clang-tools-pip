# clang-tools

[![PyPI](https://img.shields.io/pypi/v/clang-tools)](https://pypi.org/project/clang-tools/) [![Python test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml) [![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip) [![Platfrom](https://img.shields.io/badge/platform-linux--64%20%7C%20win--64%20%7C%20osx--64%20-blue)](https://pypi.org/project/clang-tools/) ![PyPI - Downloads](https://img.shields.io/pypi/dw/clang-tools)


Install clang-tools binaries (clang-format, clang-tidy) with pip.

## Install

Install `clang-tools` command with pip

```bash
# install `clang-tools` from pip
$ pip install clang-tools

# install `clang-tools` from git repo
pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main
```

## Usage

```bash
$ clang-tools --help
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
$ clang-tools --install 13
# Or install to a specified directory
$ clang-tools --install 13 --directory .

$ clang-format-13 --version
clang-format version 13.0.0

$ clang-tidy-13 --version
LLVM (http://llvm.org/):
  LLVM version 13.0.0
  Optimized build.
  Default target: x86_64-unknown-linux-gnu
  Host CPU: skylake
```

## Supported versions

### clang-format
| Version | 14 | 13 | 12.0.1 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3.9 |
|:-------:|:--:|:--:|:------:|:--:|:--:|:--:|:-:|:-:|:-:|:-:|:-:|:-:|:---:|
|  Linux  |  ✔️ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |
| Windows |  ✔️ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |
|  macOS  |  ✔️ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |

### clang-tidy

| Version | 14 | 13 | 12.0.1 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3.9 |
|:-------:|:--:|:--:|:------:|:--:|:--:|:--:|:-:|:-:|:-:|:-:|:-:|:-:|:---:|
|  Linux  |  ❌ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |
| Windows |  ✔️ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |
|  macOS  |  ✔️ |  ✔️ | ✔️  |  ✔️ |  ✔️ |  ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |  ✔️  |

Know issue: clang-tidy version 14 has Segmentation fault (core dumped).

Thanks to the project [clang-tools-static-binaries](https://github.com/muttleyxd/clang-tools-static-binaries) for all the binaries.
