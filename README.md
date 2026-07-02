[![PyPI version](https://img.shields.io/pypi/v/clang-tools?color=blue)](https://pypi.org/project/clang-tools/)
[![Platform](https://img.shields.io/badge/platform-linux--64%20%7C%20linux--arm64%20%7C%20win--64%20%7C%20win--arm64%20%7C%20osx--64%20%7C%20osx--arm64-blue)](https://pypi.org/project/clang-tools/)
[![Test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip)
[![Downloads](https://img.shields.io/pypi/dw/clang-tools)](https://pypistats.org/packages/clang-tools)
[![cpp-linter hub](https://img.shields.io/badge/%F0%9F%8F%A0_cpp--linter_hub-%E2%86%90_home-22863a)](https://cpp-linter.github.io/)

Easily install `clang-format`, `clang-tidy`, `clang-query`, `clang-apply-replacements`, `clang-include-cleaner`, `llvm-cov`, `llvm-profdata`, `llvm-symbolizer`, and `clang-scan-deps` static binaries or
Python wheels using the `clang-tools` CLI.

> [!IMPORTANT]
> This package only manages binary executables
> (& corresponding symbolic links) that are installed using this
> package's executable script. It does not intend to change or modify
> any binary executable installed from other sources (like LLVM
> releases).
>
> For Python wheels, this CLI supports `clang-format`, `clang-tidy`,
> `clang-include-cleaner`, and `clang-apply-replacements` tools.

📖 **Full documentation:** [cpp-linter.github.io/clang-tools-pip](https://cpp-linter.github.io/clang-tools-pip/)

## Features

- Install `clang-format`, `clang-tidy`, `clang-query`, `clang-apply-replacements`, `clang-include-cleaner`, `llvm-cov`, `llvm-profdata`, `llvm-symbolizer`, and `clang-scan-deps` via a single `clang-tools` CLI.
- Supports both **static binaries** (standalone executables) and **Python wheels** (installed via pip).
- Automatically uses static binaries when available; falls back to wheels if not.
- Works on Linux, macOS, and Windows (x86_64 and ARM64).
- Choose a specific LLVM version (12–22) or install the latest.
- Install only the tools you need with `--tool`.
- Uses SHA512 checksums to verify downloaded binaries.
- Creates unversioned symlinks (e.g., `clang-format`) alongside versioned binaries (`clang-format-18`) for convenience.

  > [!NOTE]
  > To create symbolic links on Windows, you must enable developer mode
  > from the Windows settings under "Privacy & security" > "For developers"
  > category.

- Install to any directory with `--directory`.
- Uninstall with `clang-tools uninstall`.

## Install clang-tools CLI

> [!TIP]
> It is recommended to use this package in a virtual environment.
>
> ```bash
> python -m venv env-name
> source env-name/bin/activate  # Linux
> ./env-name/Scripts/activate   # Windows
> ```

Install `clang-tools` command with pip:

```bash
pip install clang-tools
```

Install `clang-tools` from git repo:

```bash
pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main
```

## CLI Usage

For a full list of CLI options, see the [documentation](https://cpp-linter.github.io/clang-tools-pip/).

### Install binaries

```bash
# Install latest clang-format (auto-detects: tries binary with --version, else wheel)
clang-tools install clang-format

# Install specific version (auto-detect: binary first, fall back to wheel)
clang-tools install clang-format --version 13

# Install multiple tools with a version
clang-tools install clang-format clang-tidy --version 13

# Install to a specified directory
clang-tools install clang-format --version 13 --directory .

```

If the installed directory is in your path:

```bash
clang-format-13 --version
# clang-format version 13.0.0
```

> [!NOTE]
> Wheel installation resolves the latest matching version from PyPI
> (e.g. `--version 18` finds `18.1.8`). If you know the exact version,
> `pip install <tool>==<version>` is equivalent and more direct.

### Install wheels

To install specific tools as Python wheels:

```bash
# Install latest clang-format wheel
clang-tools install clang-format --version 21

# Install latest clang-tidy wheel
clang-tools install clang-tidy --version 21
```

## Supported Clang Tools

### clang tools binaries

- clang-format
- clang-tidy
- clang-query
- clang-apply-replacements
- clang-include-cleaner
- llvm-cov
- llvm-profdata
- llvm-symbolizer
- clang-scan-deps

For more details, visit [clang-tools-static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries).

### clang tools Python wheels

- [clang-format](https://pypi.org/project/clang-format/#history)
- [clang-tidy](https://pypi.org/project/clang-tidy/#history)
- [clang-include-cleaner](https://pypi.org/project/clang-include-cleaner/#history)
- [clang-apply-replacements](https://pypi.org/project/clang-apply-replacements/#history)

Check the respective PyPI pages for available versions and platform support.

## License

This project is licensed under the [MIT License](LICENSE).
