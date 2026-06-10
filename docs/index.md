[![PyPI version](https://img.shields.io/pypi/v/clang-tools?color=blue)](https://pypi.org/project/clang-tools/)
[![Test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip)
[![Platform](https://img.shields.io/badge/platform-linux--64%20%7C%20linux--arm64%20%7C%20win--64%20%7C%20osx--64%20%7C%20osx--arm64%20-blue)](https://pypi.org/project/clang-tools/)
[![Downloads](https://img.shields.io/pypi/dw/clang-tools)](https://pypistats.org/packages/clang-tools)

Easily install `clang-format`, `clang-tidy`, `clang-query`, and
`clang-apply-replacements` static binaries or Python wheels using the
`clang-tools` CLI.

!!! important
    This package only manages binary executables
    (& corresponding symbolic links) that are installed using this package's
    executable script. It does not intend to change or modify any binary
    executable installed from other sources (like LLVM releases).

    For Python wheels, this CLI only supports `clang-format` and
    `clang-tidy` tools.

## Features

- Support clang tools binaries and Python wheels.
- Binaries are statically linked for improved portability.
- Binaries can be specified or installed for increased flexibility.
- Binaries are checked with SHA512 checksum. This ensures:
    1. Downloads are not corrupted.
    2. Old binary builds can be updated.
- Installed binaries are symbolically linked for better cross-platform usage.
  For example (on Windows), the `clang-tidy-13.exe` binary executable can
  also be invoked with the symbolic link titled `clang-tidy.exe`

    !!! note
        To create symbolic links on Windows, you must enable developer mode
        from the Windows settings under "Privacy & security" > "For developers"
        category.
- Customizable install path.

## Install clang-tools CLI

!!! tip
    It is recommended to use this package in a virtual environment.

        # create the virtual env in the working directory
        python -m venv env-name

        # to activate on Linux:
        source env-name/bin/activate

        # to activate on Windows:
        ./env-name/Scripts/activate

    This will ensure that

    1. there are no permission problems when installing the tool
    2. the installed path (for MacOS and Windows) is within the environment's
       variable `PATH`.

Install `clang-tools` command with pip:

    pip install clang-tools

Install `clang-tools` from git repo:

    pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main

## CLI Usage

For a list of supported Command Line Interface options, see:

- [`clang-tools` CLI Reference](cli_args.md)
- [`clang-tools-wheel` CLI Reference](wheel_cli_args.md)

### Install binaries examples

Use `clang-tools` command to install version 13 binaries:

    clang-tools --install 13

Or install to a specified directory:

    clang-tools --install 13 --directory .

Or install a specified tool, such as `clang-format` and
`clang-query` version 14:

    clang-tools --install 14 --tool clang-format clang-query

If the installed directory is in your path, you can run the installed tools:

    clang-format-13 --version
    # clang-format version 13.0.0

    clang-tidy-13 --version
    # LLVM (http://llvm.org/):
    #   LLVM version 13.0.0
    #   Optimized build.
    #   Default target: x86_64-unknown-linux-gnu
    #   Host CPU: skylake

### Install wheels examples

After installing the `clang-tools` CLI, you can install the
Python wheels using the `clang-tools-wheel` command.

!!! important
    The `clang-tools-wheel` command is primarily intended for
    cpp-linter projects to simplify installing clang tools Python wheels.
    For general use, it is recommended to install the wheels directly
    using `pip`, `pipx`, `uv`, or similar tools.

    # Install latest clang-format wheel
    clang-tools-wheel --tool clang-format
    # Install specific version clang-format wheel
    clang-tools-wheel --tool clang-format --version 21

    # Install latest clang-tidy wheel
    clang-tools-wheel --tool clang-tidy
    # Install specific version clang-tidy wheel
    clang-tools-wheel --tool clang-tidy --version 21

## Supported Versions

### clang tools binaries

The following table shows the supported versions of clang-format,
clang-tidy, clang-query, and clang-apply-replacements binaries
for each platform:

| Platform | 22 | 21 | 20 | 19 | 18 | 17 | 16 | 15 | 14 | 13 | 12 | 11 |
|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| Linux | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| Windows | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| macOS | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |

For more details, visit the
[clang-tools-static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries)
repository.

### clang tools Python wheels

The following Python wheels are supported:

- [clang-format](https://pypi.org/project/clang-format/#history)
- [clang-tidy](https://pypi.org/project/clang-tidy/#history)

Check the respective PyPI pages for available versions and platform support.
