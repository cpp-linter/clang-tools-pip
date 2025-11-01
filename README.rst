clang-tools CLI
===============

.. |latest-version| image:: https://img.shields.io/pypi/v/clang-tools?color=blue
    :target: https://pypi.org/project/clang-tools/
    :alt: PyPI
.. |test| image:: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml/badge.svg
    :target: https://github.com/cpp-linter/clang-tools-pip/actions/workflows/test.yml
    :alt: test
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

|latest-version| |test| |codecov-badge| |sonar-badge| |platform-badge| |pypi-badge|


Easily install clang-format, clang-tidy, clang-query, and clang-apply-replacements static binaries or Python wheels using the ``clang-tools`` CLI.


.. important::
    This package only manages binary executables (& corresponding symbolic links) that
    are installed using this package's executable script. It does not intend to change or
    modify any binary executable installed from other sources (like LLVM releases).

    For Python wheels, this CLI only support clang-format and clang-tidy tools.

Features
--------

- Support clang tools binaries and Python wheels.
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

Install ``clang-tools`` command with pip

.. code-block:: shell

    pip install clang-tools

Install ``clang-tools`` from git repo

.. code-block:: shell

    pip install git+https://github.com/cpp-linter/clang-tools-pip.git@main


CLI Usage
---------

For a list of supported Command Line Interface options, see
`the CLI documentation <https://cpp-linter.github.io/clang-tools-pip/cli_args.html>`_

Install binaries examples
~~~~~~~~~~~~~~~~~~~~~~~~~

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


Install wheels examples
~~~~~~~~~~~~~~~~~~~~~~~~~

After installing the ``clang-tools`` CLI, you can install the Python wheels using the ``clang-tools-wheel`` command.

.. important::

    The ``clang-tools-wheel`` command is primarily intended for cpp-linter projects to simplify installing clang tools Python wheels.
    For general use, it is recommended to install the wheels directly using ``pip``, ``pipx``, ``uv``, or similar tools.


.. code-block:: shell

    # Install latest clang-format wheel
    clang-tools-wheel --tool clang-format
    # Install specific version clang-format wheel
    clang-tools-wheel --tool clang-format --version 21

    # Install latest clang-tidy wheel
    clang-tools-wheel --tool clang-tidy
    # Install specific version clang-tidy wheel
    clang-tools-wheel --tool clang-tidy --version 21


Supported Versions
------------------


clang tools binaries
~~~~~~~~~~~~~~~~~~~~

The following table shows the supported versions of clang-format, clang-tidy, clang-query, and clang-apply-replacements binaries for each platform:

.. csv-table::
    :header: "Platform", "21", "20", "19", "18", "17", "16", "15", "14", "13", "12", "11", "10", "9"
    :stub-columns: 1

    Linux,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    Windows,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️
    macOS,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️,✔️

For more details, visit the `clang-tools-static-binaries <https://github.com/cpp-linter/clang-tools-static-binaries>`_ repository.

clang tools Python wheels
~~~~~~~~~~~~~~~~~~~~~~~~~

The following Python wheels are supported:

- `clang-format <https://pypi.org/project/clang-format/#history>`_
- `clang-tidy <https://pypi.org/project/clang-tidy/#history>`_

Check the respective PyPI pages for available versions and platform support.
