# clang-tools

[![PyPI](https://img.shields.io/pypi/v/clang-tools?labelColor=454a63&color=007ec6)](https://pypi.org/project/clang-tools/)
[![ci](https://img.shields.io/github/actions/workflow/status/cpp-linter/clang-tools-pip/test.yml?branch=main&label=ci&labelColor=454a63)](https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml)
[![coverage](https://img.shields.io/codecov/c/github/cpp-linter/clang-tools-pip?labelColor=454a63)](https://codecov.io/gh/cpp-linter/clang-tools-pip)
[![part of cpp-linter](https://img.shields.io/badge/part%20of-cpp--linter-ffc20a?labelColor=454a63)](https://cpp-linter.github.io/)

Install `clang-format`, `clang-tidy` and other LLVM tools without building LLVM, as static binaries
or Python wheels, using the `clang-tools` CLI.

[Website](https://cpp-linter.github.io/) ·
[Documentation](https://cpp-linter.github.io/clang-tools-pip/) ·
[Get started](https://cpp-linter.github.io/getting-started/#just-the-clang-tools) ·
[Discussions](https://github.com/orgs/cpp-linter/discussions)

## Quick start

```bash
pip install clang-tools
clang-tools install clang-format clang-tidy --version 21
```

This installs the LLVM 21 static binaries `clang-format-21` and `clang-tidy-21`. Without
`--directory`, they go to `~/.local/bin` on Linux, and on macOS and Windows to the folder that
holds the Python executable (the `bin` or `Scripts` folder of a virtual environment).
A `--directory` that doesn't exist is created, but the parent folder(s) must exist.

> [!TIP]
> It is recommended to use this package in a virtual environment.
>
> ```bash
> python -m venv env-name
> source env-name/bin/activate  # Linux and macOS
> ./env-name/Scripts/activate   # Windows
> ```

## Usage

`clang-tools install` with `--version` installs the static binary. It falls back to the wheel when
there is no static binary for that version, tool or platform, or when the download fails; any other
error stops the command. Without `--version`, it installs the latest wheel. For a full list of CLI
options, see the [CLI reference](https://cpp-linter.github.io/clang-tools-pip/cli_args/).

### Install binaries

```bash
# Install a specific version (binary first, falls back to the wheel)
clang-tools install clang-format --version 21

# Install to a specified directory
clang-tools install clang-format --version 21 --directory .
```

If the installed directory is in your path:

```bash
clang-format-21 --version
# clang-format version 21.1.0
```

To uninstall, give the tool names and the version:

```bash
clang-tools uninstall clang-format --version 21 --directory .
```

- Uses SHA512 checksums to verify downloaded binaries.
- Keeps each downloaded binary in a data directory, one folder per release, and puts a link
  to it (e.g., `clang-format-21`) in the install directory. Installing the same version again,
  in any directory, doesn't download it again.
- Installs clang's builtin headers (`stddef.h`, `stdarg.h`, ...) next to clang-tidy, clang-query,
  clang-include-cleaner and clang-scan-deps, so they can parse code that includes system headers.
- Creates unversioned symlinks (e.g., `clang-format`) alongside versioned binaries (`clang-format-21`) for convenience.
- If the versioned binary (e.g., `clang-format-21`) is already on your PATH, links to it instead of downloading.

The data directory is `~/.local/share/clang-tools` on Linux (or `$XDG_DATA_HOME/clang-tools`),
`~/Library/Application Support/clang-tools` on macOS and `%LOCALAPPDATA%\clang-tools` on Windows.
Set `CLANG_TOOLS_DATA_DIR` to use another directory. `clang-tools uninstall` removes the links, not
the data directory; delete it to free the space.

> [!NOTE]
> To create symbolic links on Windows, you must enable
> [Developer Mode](https://learn.microsoft.com/en-us/windows/advanced-settings/developer-mode).
> Without it, the binaries are copied to the install directory. On Windows, clang's builtin
> headers are also copied to `<install directory>\..\lib\clang`, because clang (LLVM 12 to 17 at
> least) looks for them next to the link rather than next to the binary it points to.

> [!IMPORTANT]
> This package only manages binary executables
> (& corresponding symbolic links) that are installed using this
> package's executable script. It does not intend to change or modify
> any binary executable installed from other sources (like LLVM
> releases).

### Install wheels

Without `--version`, the latest wheel is installed from PyPI:

```bash
# Install the latest clang-format wheel
clang-tools install clang-format

# Install the latest clang-tidy wheel
clang-tools install clang-tidy
```

Wheels are installed with pip into the Python environment that runs `clang-tools`, so that
environment needs pip. `--directory` does not apply to wheels, and `clang-tools uninstall` does not
remove them; use `pip uninstall <tool>`.

> [!NOTE]
> Wheel installation resolves the latest matching version from PyPI
> (e.g. `--version 18` finds `18.1.8`). If you know the exact version,
> `pip install <tool>==<version>` is equivalent and more direct.

### Install the development version

```bash
pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main
```

## Supported versions

### clang tools binaries

Every LLVM version listed in the
[index](https://cpp-linter.github.io/clang-tools-static-binaries/index.json) (LLVM 12 to 23 today),
for Linux, macOS and Windows on x86-64 and ARM64:

- clang-format
- clang-tidy
- clang-query
- clang-apply-replacements
- clang-include-cleaner (LLVM 18 and later)
- llvm-cov
- llvm-profdata
- llvm-symbolizer
- clang-scan-deps

For more details, visit [clang-tools-static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries).

### clang tools Python wheels

- [clang-format](https://pypi.org/project/clang-format/#history)
- [clang-tidy](https://pypi.org/project/clang-tidy/#history)
- [clang-include-cleaner](https://pypi.org/project/clang-include-cleaner/#history) (LLVM 22)
- [clang-apply-replacements](https://pypi.org/project/clang-apply-replacements/#history) (LLVM 16 and later)

Only these four tools have wheels, so the other tools need `--version`. Check the respective PyPI
pages for available versions and platform support.

## Contributing

See the [contributing guide](https://github.com/cpp-linter/clang-tools-pip/blob/main/CONTRIBUTING.md)
and [open an issue](https://github.com/cpp-linter/clang-tools-pip/issues) for bugs and feature requests.

## License

This project is licensed under the [MIT License](https://github.com/cpp-linter/clang-tools-pip/blob/main/LICENSE).
