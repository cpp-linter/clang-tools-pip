The `clang-tools` package exposes the following Python modules:

## `clang_tools.main`

Main entry point for the unified `clang-tools` CLI.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/main.py)

Provides the `clang-tools` command-line interface for installing
and managing clang tool binaries and Python wheels.

---

## `clang_tools.install`

Installation logic for clang tool binaries.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/install.py)

Handles downloading, verifying (SHA512), and symlinking clang tool
binaries from static binary releases.

---

## `clang_tools.util`

Utility functions shared across the package.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/util.py)

---

## `clang_tools.wheel_install`

Installs a tool from its wheel on PyPI, without pip.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/wheel_install.py)

Used by `clang-tools install` when a tool has no static binary for the requested
version or platform.
