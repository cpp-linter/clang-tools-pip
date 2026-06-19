"""
``clang_tools.main``
--------------------

The unified CLI entry point for installing and managing clang-tools.

Supports two installation backends — binary (static builds) and wheel (PyPI)
— via the ``--backend`` flag or auto-detection.

Usage::

    # Install one or more tools with auto-detected backend
    clang-tools install clang-format clang-tidy --version 18

    # Install latest version (wheel only, no version needed)
    clang-tools install clang-format

    # Explicitly choose backend
    clang-tools install clang-format --version 18 --backend binary
    clang-tools install clang-format --backend wheel

    # Uninstall
    clang-tools uninstall clang-format --version 12
"""

import argparse
import sys
from typing import Optional

from .install import install_clang_tools, uninstall_clang_tools
from . import RESET_COLOR, YELLOW
from .util import Version


#: Known tool names commonly installed as Python wheels.
#: With dynamic PyPI version resolution, any clang tool available on PyPI
#: can be installed, but these are the canonical ones.
WHEEL_TOOLS = {
    "clang-format",
    "clang-tidy",
    "clang-include-cleaner",
    "clang-apply-replacements",
}


def _wheel_install(tools: list[str], version: Optional[str]) -> int:
    """Install tool(s) as Python wheels.

    Tool versions are resolved dynamically from the PyPI JSON API —
    no hardcoded list is maintained in-tree.

    :returns: exit code (0 on success, 1 on failure).
    """
    from .wheel_install import resolve_wheel_install

    ok = True
    for tool in tools:
        path, error = resolve_wheel_install(tool, version)
        if error is not None:
            print(f"{YELLOW}{error}{RESET_COLOR}", file=sys.stderr)
            ok = False
        elif path:
            version_str = f" version {version}" if version else " latest version"
            print(f"{tool}{version_str} installed at: {path}")
        else:
            print(f"Failed to install {tool}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


# ---------------------------------------------------------------------------
#  Backend handlers
# ---------------------------------------------------------------------------


def _install_binary(
    tools: list[str],
    version: Optional[str],
    directory: str,
    overwrite: bool,
    no_progress_bar: bool,
) -> int:
    """Install tool(s) using the binary (static build) backend.

    ``--version`` is required for this backend.
    """
    if version is None:
        print(
            f"{YELLOW}Error: --backend binary requires --version{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1
    v = Version(version)
    if v.info == (0, 0, 0):
        print(
            f"{YELLOW}The version specified is not a semantic"
            f" specification{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1
    try:
        install_clang_tools(v, tools, directory, overwrite, no_progress_bar)
        return 0
    except (OSError, ValueError) as exc:
        print(
            f"{YELLOW}Binary install failed: {exc}{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1


def _install_wheel(tools: list[str], version: Optional[str]) -> int:
    """Install tool(s) using the wheel (PyPI) backend.

    Each tool must be in :data:`WHEEL_TOOLS`.
    """
    for tool in tools:
        if tool not in WHEEL_TOOLS:
            print(
                f"{YELLOW}Error: '{tool}' is not available as a"
                f" wheel. Supported: "
                f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1
    return _wheel_install(tools, version)


def _install_auto(
    tools: list[str],
    version: Optional[str],
    directory: str,
    overwrite: bool,
    no_progress_bar: bool,
) -> int:
    """Auto-detect: try binary first (when ``--version`` given), fall back to wheel.

    When no ``--version`` is provided, only wheel installation is possible.
    """
    if version is not None:
        v = Version(version)
        if v.info != (0, 0, 0):
            try:
                install_clang_tools(
                    v, tools, directory, overwrite, no_progress_bar
                )
                return 0
            except (OSError, ValueError) as exc:
                print(
                    f"{YELLOW}Binary install failed"
                    f" ({exc}), falling back to"
                    f" wheel...{RESET_COLOR}",
                    file=sys.stderr,
                )
    # fall back to wheel
    for tool in tools:
        if tool not in WHEEL_TOOLS:
            print(
                f"{YELLOW}Unknown tool '{tool}'. Expected one of: "
                f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1
    return _wheel_install(tools, version)


def _handle_install(args: argparse.Namespace) -> int:
    """Dispatch ``install`` subcommand based on ``--backend``."""
    tools = args.tools
    version = args.explicit_version
    directory = args.directory
    overwrite = args.overwrite
    no_progress_bar = args.no_progress_bar

    if args.backend == "binary":
        return _install_binary(tools, version, directory, overwrite, no_progress_bar)
    if args.backend == "wheel":
        return _install_wheel(tools, version)
    return _install_auto(tools, version, directory, overwrite, no_progress_bar)


# ---------------------------------------------------------------------------
#  Parser
# ---------------------------------------------------------------------------


def get_parser() -> argparse.ArgumentParser:
    """Get a parser to interpret CLI args (unified entry point)."""
    parser = argparse.ArgumentParser(
        description="Install and manage clang-tools (clang-format, clang-tidy, etc.)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- ``clang-tools install <tool> [<tool> ...]`` --------------------
    install_p = subparsers.add_parser("install", help="Install clang-tools")
    install_p.add_argument(
        "tools",
        nargs="+",
        metavar="TOOL",
        help="Tool name(s) to install (e.g. clang-format clang-tidy)",
    )
    install_p.add_argument(
        "--version",
        dest="explicit_version",
        default=None,
        metavar="VER",
        help="Version to install (e.g. 18). Required for --backend binary.",
    )
    install_p.add_argument(
        "--backend",
        choices=("auto", "binary", "wheel"),
        default="auto",
        help="Installation backend: auto (default, binary\u2192wheel), binary, or wheel",
    )
    install_p.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The directory where the clang-tools are installed.",
    )
    install_p.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="Force overwriting the symlink to the installed binary.",
    )
    install_p.add_argument(
        "-b",
        "--no-progress-bar",
        action="store_true",
        help="Do not display a progress bar for downloads.",
    )

    # --- ``clang-tools uninstall <tool> [<tool> ...] --version VER`` ----
    uninstall_p = subparsers.add_parser("uninstall", help="Uninstall clang-tools")
    uninstall_p.add_argument(
        "tools",
        nargs="+",
        metavar="TOOL",
        help="Tool name(s) to uninstall (e.g. clang-format clang-tidy)",
    )
    uninstall_p.add_argument(
        "--version",
        required=True,
        metavar="VER",
        help="Version to uninstall (e.g. 18)",
    )
    uninstall_p.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The directory from which to uninstall the tools.",
    )

    return parser


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Unified entry point for the CLI program.

    :returns: exit code (0 on success, 1 on failure).
    """
    parser = get_parser()
    args = parser.parse_args()

    if args.command is None:
        print(
            f"{YELLOW}Nothing to do. Use 'install' or 'uninstall'"
            f" subcommand.{RESET_COLOR}",
            file=sys.stderr,
        )
        parser.print_help()
        return 0

    if args.command == "install":
        return _handle_install(args)

    if args.command == "uninstall":
        uninstall_clang_tools(args.tools, args.version, args.directory)
        return 0

    return 0  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
