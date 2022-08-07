clang-tools Introduction
========================

.. image:: https://img.shields.io/pypi/v/clang-tools
    :target: https://pypi.org/project/clang-tools/
    :alt: PyPI
.. image:: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml/badge.svg
    :target: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml
    :alt: Python test
.. image:: https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR
    :target: https://codecov.io/gh/cpp-linter/clang-tools-pip
    :alt: codecov
.. image:: https://img.shields.io/badge/platform-linux--64%20%7C%20win--64%20%7C%20osx--64%20-blue
    :target: https://pypi.org/project/clang-tools/)
    :alt: Platfrom
.. image:: https://img.shields.io/pypi/dw/clang-tools
    :alt: PyPI - Downloads


Install clang-tools binaries (clang-format, clang-tidy) with pip.

Install
-------

Install `clang-tools` command with pip

.. code-block:: shell

    pip install clang-tools

Install `clang-tools` from git repo

.. code-block:: shell

    pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main

Usage
-----

.. code-block:: shell

    clang-tools --help
    usage: clang-tools [-h] [-i INSTALL] [-d DIRECTORY]

    optional arguments:
      -h, --help            show this help message and exit
      -i INSTALL, --install INSTALL
                            Install clang-tools with specific version. default is 12.
      -d DIRECTORY, --directory DIRECTORY
                            The directory where is the clang-tools install.

Use ``clang-tools`` command to install version 13 binaries.

.. code-block:: shell

    clang-tools --install 13

Or install to a specified directory

.. code-block:: shell

    clang-tools --install 13 --directory .

If the installed directory is in your path, you can run the installed tools.

.. code-block:: shell

    clang-format-13 --version
    clang-format version 13.0.0

.. code-block:: shell

    clang-tidy-13 --version
    LLVM (http://llvm.org/):
      LLVM version 13.0.0
      Optimized build.
      Default target: x86_64-unknown-linux-gnu
      Host CPU: skylake

Supported versions
------------------

clang-format
************
.. csv-table::
    :header: "Version", "14", "13", "12.0.1", "12", "11", "10", "9", "8", "7", "6", "5", "4", "3.9"
    :stub-columns: 1

    Linux,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    Windows,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    macOS,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️

clang-tidy
**********
.. csv-table::
    :header: "Version", "14", "13", "12.0.1", "12", "11", "10", "9", "8", "7", "6", "5", "4", "3.9"
    :stub-columns: 1

    Linux,❌,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    Windows,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    macOS,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️

Know issues:

1. clang-tidy-14 has Segmentation fault on Ubuntu 22.02.
2. clang-format-14 is over 1 GB for MacOSX

Thanks to the project
`clang-tools-static-binaries <https://github.com/muttleyxd/clang-tools-static-binaries>`_
for all the binaries.