The `clang-tools` package exposes the following Python modules:

## `clang_tools.main`

Main entry point for the `clang-tools` CLI.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/main.py)

Provides the `clang-tools` command-line interface for installing
and managing clang tool binaries.

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

## `clang_tools.wheel`

Python wheel installation entry point.

[:octicons-code-16: View source](https://github.com/cpp-linter/clang-tools-pip/blob/main/clang_tools/wheel.py)

Provides the `clang-tools-wheel` command-line interface for installing
clang tool Python wheels.
