# clang-tools Introduction

[![PyPI](https://img.shields.io/pypi/v/clang-tools)](https://pypi.org/project/clang-tools/)
[![Python test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![sonarcloud](https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip)
[![Platfrom](https://img.shields.io/badge/platform-linux--64%20%7C%20win--64%20%7C%20osx--64%20-blue)](https://pypi.org/project/clang-tools/)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/clang-tools)](https://pypistats.org/packages/clang-tools)


**Install clang-tools binaries (clang-format, clang-tidy, clang-query and clang-apply-replacements) with pip.**

> [!IMPORTANT]
> This package only manages binary executables (& corresponding symbolic links) that are installed using this package's executable script. It does not intend to change or modify any binary executable installed from other sources (like LLVM releases).

## Features

- Binaries are statically linked for improved portability.
- Binaries can be specified installed for increased flexibility.
- Binaries are checked with SHA512 checksum. This ensures:

  1. Downloads are not corrupted.
  2. Old binary builds can be updated.

- Installed binaries are symbolically linked for better cross-platform usage.

  For example (on Windows), the `clang-tidy-13.exe` binary executable can
  also be invoked with the symbolic link titled `clang-tidy.exe`

- Customizable install path.


## Install

> [!TIP]
> It is recommended to use this package in a virtual environment.

```sh
# create the virtual env in the working directory
python -m venv env-name

# to activate on Linux:
source env-name/bin/activate

# to activate on Windows:
./env-name/Scripts/activate
```

This will ensure that

1. there are no permission problems when installing the tool
2. the installed path (for MacOS and Windows) is within the environment's variable `PATH`.

### Install `clang-tools` command with pip

```sh
pip install clang-tools
```

### Install `clang-tools` from git repo

```sh
pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main
```

## `clang-tools` usage

For a list of supported Command Line Interface options, see [the CLI documentation](https://cpp-linter.github.io/clang-tools-pip/cli_args.html).

### Examples

Use ``clang-tools`` command to install version 13 binaries.

```bash
clang-tools --install 13
```

Or install to a specified directory

```bash
clang-tools --install 13 --directory .
```

Or install a specified tool, such as clang-format and clang-query version 14.

```bash
clang-tools --install 14 --tool clang-format clang-query
```

If the installed directory is in your path, you can run the installed tools.

```bash
clang-format-13 --version
clang-format version 13.0.0

clang-tidy-13 --version
LLVM (http://llvm.org/):
    LLVM version 13.0.0
    Optimized build.
    Default target: x86_64-unknown-linux-gnu
    Host CPU: skylake
```


## Supported versions

clang-format, clang-tidy, clang-query, clang-apply-replacements supports versions

| Version | 17 | 16 | 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 |
|---------|----|----|----|----|----|----|----|----|---|---|---|
| Linux   |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |
| Windows |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |
| macOS   |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |✔️ |


> [!WARNING]
> All clang-tidy v14+ builds for MacOS are still ~1.7 GB in size.

------------

Thanks to the project [clang-tools-static-binaries](https://github.com/muttleyxd/clang-tools-static-binaries).
We now used the [fork repository](https://github.com/cpp-linter/clang-tools-static-binaries) that fixed the clang-tidy v14+ Segmentation fault (core dumped).
see [#56](https://github.com/cpp-linter/clang-tools-pip/issues/56) for details.
