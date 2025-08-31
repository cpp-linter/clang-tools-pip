clang-tools CLI
===============

**Install clang-format, clang-tidy, clang-query, and clang-apply-replacements binaries with clang-tools CLI.**

.. |latest-version| image:: https://img.shields.io/pypi/v/clang-tools?color=blue
    :target: https://pypi.org/project/clang-tools/
    :alt: PyPI
.. |python-test| image:: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml/badge.svg
    :target: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/python-test.yml
    :alt: Python test
.. |codecov-badge| image:: https://codecov.io/gh/cpp-linter/clang-tools-pip/branch/main/graph/badge.svg?token=40G5ZOIRRR
    :target: https://codecov.io/gh/cpp-linter/clang-tools-pip
    :alt: codecov
.. |sonar-badge| image:: https://sonarcloud.io/api/project_badges/measure?project=cpp-linter_clang-tools-pip&metric=alert_status
    :target: https://sonarcloud.io/summary/new_code?id=cpp-linter_clang-tools-pip
    :alt: sonarcloud
.. |platform-badge| image:: https://img.shields.io/badge/platform-linux--64%20%7C%20win--64%20%7C%20osx--64%20-blue
    :target: https://pypi.org/project/clang-tools/
    :alt: Platform
.. |pypi-badge| image:: https://img.shields.io/pypi/dw/clang-tools
    :target: https://pypistats.org/packages/clang-tools
    :alt: PyPI - Downloads

|latest-version| |python-test| |codecov-badge| |sonar-badge| |platform-badge| |pypi-badge|

.. important::
    This package only manages binary executables (& corresponding symbolic links) that
    are installed using this package's executable script. It does not intend to change or
    modify any binary executable installed from other sources (like LLVM releases).

Features
--------

- Binaries are statically linked for improved portability.
- Binaries can be specified installed for increased flexibility.
- Binaries are checked with SHA512 checksum. This ensures:

  1. Downloads are not corrupted.
  2. Old binary builds can be updated.
- Installed binaries are symbolically linked for better cross-platform usage.
  For example (on Windows), the ``clang-tidy-13.exe`` binary executable can
  also be invoked with the symbolic link titled ``clang-tidy.exe``

  .. note::
      To create symbolic links on Windows, you must enable developer mode
      from the Windows settings under "Privacy & security" > "For developers"
      category.
- Customizable install path.

Install clang-tools CLI
-----------------------

.. tip::
    It is recommended to use this package in a virtual environment.

    .. code-block:: bash

        # create the virtual env in the working directory
        python -m venv env-name

        # to activate on Linux:
        source env-name/bin/activate

        # to activate on Windows:
        ./env-name/Scripts/activate

    This will ensure that

    1. there are no permission problems when installing the tool
    2. the installed path (for MacOS and Windows) is within the environment's
       variable ``PATH``.

Install `clang-tools` command with pip

.. code-block:: shell

    pip install clang-tools

Install `clang-tools` from git repo

.. code-block:: shell

    pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main

CLI Usage
---------

For a list of supported Command Line Interface options, see
`the CLI documentation <https://cpp-linter.github.io/clang-tools-pip/cli_args.html>`_

Examples
********

Use ``clang-tools`` command to install version 13 binaries.

.. code-block:: shell

    clang-tools --install 13

Or install to a specified directory

.. code-block:: shell

    clang-tools --install 13 --directory .

Or install a specified tool, such as clang-format and clang-query version 14.

.. code-block:: shell

    clang-tools --install 14 --tool clang-format clang-query

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

clang-format, clang-tidy, clang-query, clang-apply-replacements
***************************************************************
.. csv-table::
    :header: "Version", "21", "20", "19", "18", "17", "16", "15", "14", "13", "12", "11", "10", "9"
    :stub-columns: 1

    Linux,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    Windows,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    macOS,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️

For more details, visit the `clang-tools-static-binaries <https://github.com/cpp-linter/clang-tools-static-binaries>`_ repository.
