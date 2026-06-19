"""
``clang_tools.main``
--------------------

The unified CLI entry point for installing and managing clang-tools.

Usage::

    # Install one or more tools (auto-detect: binary→wheel)
    clang-tools install clang-format clang-tidy --version 18

    # Install latest version (wheel only, no version needed)
    clang-tools install clang-format

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


def _handle_install(args: argparse.Namespace) -> int:
    """Handle ``install`` subcommand — auto-detect backend.

    When ``--version`` is given, binary (static build) is tried first;
    on failure it falls back to wheel (PyPI pip install).
    Without ``--version``, only wheel is possible.
    """
    tools = args.tools
    version = args.explicit_version
    directory = args.directory
    overwrite = args.overwrite
    no_progress_bar = args.no_progress_bar

    if version is not None:
        v = Version(version)
        if v.info != (0, 0, 0):
            try:
                install_clang_tools(v, tools, directory, overwrite, no_progress_bar)
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
        help="Version to install (e.g. 18). When specified, binary install"
        " is tried first, falling back to wheel.",
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

    # --- ``clang-tools version`` ------------------------------------------
    subparsers.add_parser(
        "version",
        help="Show the clang-tools package version",
    )

    return parser


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------


def _print_version() -> None:
    """Print the installed version of clang-tools-pip and exit."""
    try:
        from importlib.metadata import version

        ver = version("clang-tools")
    except ImportError:
        ver = "unknown"
    print(f"clang-tools {ver}")


def main() -> int:
    """Unified entry point for the CLI program.

    :returns: exit code (0 on success, 1 on failure).
    """
    # Handle ``--version`` at the root level before argparse to avoid
    # conflicting with ``install --version``.
    if len(sys.argv) == 2 and sys.argv[1] in ("--version", "-V"):
        _print_version()
        return 0

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

    if args.command == "version":
        _print_version()
        return 0

    return 0  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
