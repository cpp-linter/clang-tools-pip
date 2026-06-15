[![PyPI version](https://img.shields.io/pypi/v/clang-tools?color=blue)](https://pypi.org/project/clang-tools/)
[![Platform](https://img.shields.io/badge/platform-linux--64%20%7C%20linux--arm64%20%7C%20win--64%20%7C%20win--arm64%20%7C%20osx--64%20%7C%20osx--arm64%20-blue)](https://pypi.org/project/clang-tools/)
[![Test](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip)
[![Downloads](https://img.shields.io/pypi/dw/clang-tools)](https://pypistats.org/packages/clang-tools)
[![cpp-linter hub](https://img.shields.io/badge/%F0%9F%8F%A0_cpp--linter_hub-%E2%86%90_home-22863a)](https://cpp-linter.github.io/)

Easily install `clang-format`, `clang-tidy`, `clang-query`,
`clang-apply-replacements`, and `clang-include-cleaner` static
binaries or Python wheels using the `clang-tools` CLI.

> [!IMPORTANT]
> This package only manages binary executables
> (& corresponding symbolic links) that are installed using this
> package's executable script. It does not intend to change or modify
> any binary executable installed from other sources (like LLVM
> releases).
>
> For Python wheels, this CLI only supports `clang-format` and
> `clang-tidy` tools.

📖 **Full documentation:** [cpp-linter.github.io/clang-tools-pip](https://cpp-linter.github.io/clang-tools-pip/)

## Features

- Install and manage clang tools binaries and Python wheels.
- Binaries are statically linked (from upstream LLVM) for improved portability.
- Binaries can be specified or installed for increased flexibility.
- Binaries are checked with SHA512 checksum. This ensures:
  1. Downloads are not corrupted.
  2. Old binary builds can be updated.
- Installed binaries are symbolically linked for better cross-platform usage.
  For example (on Windows), the `clang-tidy-13.exe` binary executable can
  also be invoked with the symbolic link titled `clang-tidy.exe`

  > [!NOTE]
  > To create symbolic links on Windows, you must enable developer mode
  > from the Windows settings under "Privacy & security" > "For developers"
  > category.

- Customizable install path.

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
# Install version 13 binaries (auto-detects binary vs wheel)
clang-tools install 13

# Force binary installation
clang-tools install 13 --binary

# Install to a specified directory
clang-tools install 13 --directory .

# Install specific tools
clang-tools install 14 --tool clang-format clang-query
```

If the installed directory is in your path:

```bash
clang-format-13 --version
# clang-format version 13.0.0
```

### Install wheels

```bash
# Install latest clang-format wheel
clang-tools install clang-format --wheel

# Install specific version
clang-tools install clang-format --wheel --version 21
```

> [!IMPORTANT]
> Wheel installation is primarily intended for
> cpp-linter projects. For general use, install wheels directly
> using `pip`, `pipx`, or `uv`.

## Supported Versions

### clang tools binaries

The following table shows the supported versions of clang-format,
clang-tidy, clang-query, clang-apply-replacements, and
clang-include-cleaner (LLVM 18+) binaries for each platform:

| Platform | 22 | 21 | 20 | 19 | 18 | 17 | 16 | 15 | 14 | 13 | 12 | 11 |
|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| Linux amd64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| Linux arm64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| Windows amd64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| Windows arm64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| macOS amd64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |
| macOS arm64 | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ | ✔️ |

For more details, visit
[clang-tools-static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries).

### clang tools Python wheels

- [clang-format](https://pypi.org/project/clang-format/#history)
- [clang-tidy](https://pypi.org/project/clang-tidy/#history)

Check the respective PyPI pages for available versions and platform support.

## License

This project is licensed under the [MIT License](LICENSE).
