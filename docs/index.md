[![PyPI version](https://img.shields.io/pypi/v/clang-tools?color=blue)](https://pypi.org/project/clang-tools/)
[![Test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip)
[![Platform](https://img.shields.io/badge/platform-linux--64%20%7C%20linux--arm64%20%7C%20win--64%20%7C%20win--arm64%20%7C%20osx--64%20%7C%20osx--arm64-blue)](https://pypi.org/project/clang-tools/)
[![Downloads](https://img.shields.io/pypi/dw/clang-tools)](https://pypistats.org/packages/clang-tools)

Easily install `clang-format`, `clang-tidy`, `clang-query`,
`clang-apply-replacements`, and `clang-include-cleaner` static binaries or
Python wheels using the `clang-tools` CLI.

!!! important
    This package only manages binary executables
    (& corresponding symbolic links) that are installed using this package's
    executable script. It does not intend to change or modify any binary
    executable installed from other sources (like LLVM releases).

    For Python wheels, this CLI supports `clang-format`, `clang-tidy`,
    `clang-include-cleaner`, and `clang-apply-replacements` tools.

## Features

- Install `clang-format`, `clang-tidy`, `clang-query`, `clang-apply-replacements`, and `clang-include-cleaner` via a single `clang-tools` CLI.
- Supports both **static binaries** (standalone executables) and **Python wheels** (installed via pip).
- Automatically uses static binaries when available; falls back to wheels if not.
- Works on Linux, macOS, and Windows (x86_64 and ARM64).
- Choose a specific LLVM version (11–22) or install the latest.
- Install only the tools you need with `--tool`.
- Uses SHA512 checksums to verify downloaded binaries.
- Creates unversioned symlinks (e.g., `clang-format`) alongside versioned binaries (`clang-format-18`) for convenience.

    !!! note
        To create symbolic links on Windows, you must enable developer mode
        from the Windows settings under "Privacy & security" > "For developers"
        category.

- Install to any directory with `--directory`.
- Uninstall with `clang-tools uninstall`.

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

### Install binaries examples

Use `clang-tools` to install tools. Positional arguments are always
tool names; version is specified via `--version`:

    # Install latest clang-format (auto-detect: tries binary with --version, else wheel)
    clang-tools install clang-format

    # Install specific version (auto-detect: binary first, fall back to wheel)
    clang-tools install clang-format --version 13

    # Install to a specified directory
    clang-tools install clang-format --version 13 --directory .

    # Install multiple tools
    clang-tools install clang-format clang-tidy --version 14

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
Python wheels using the unified `clang-tools` command.

!!! important
    Wheel installation is primarily intended for
    cpp-linter projects to simplify installing clang tools Python wheels.
    For general use, it is recommended to install the wheels directly
    using `pip`, `pipx`, `uv`, or similar tools.

    ```bash
    # Install latest clang-format wheel
    clang-tools install clang-format --version 21

    # Install latest clang-tidy wheel
    clang-tools install clang-tidy --version 21
    ```

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
- [clang-include-cleaner](https://pypi.org/project/clang-include-cleaner/#history)
- [clang-apply-replacements](https://pypi.org/project/clang-apply-replacements/#history)

Check the respective PyPI pages for available versions and platform support.
