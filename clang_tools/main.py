"""
``clang_tools.main``
--------------------

The unified CLI entry point for installing and managing clang-tools.

Usage::

    # Install one or more tools (static binary, else the wheel from PyPI)
    clang-tools install clang-format clang-tidy --version 21

    # Install the newest version
    clang-tools install clang-format

    # Uninstall
    clang-tools uninstall clang-format --version 21
"""

import argparse
import sys

from . import RESET_COLOR, YELLOW
from .install import install_clang_tools, uninstall_clang_tools
from .util import RE_VERSION


def _handle_install(args: argparse.Namespace) -> int:
    """Handle the ``install`` subcommand.

    :returns: exit code (0 on success, 1 on failure).
    """
    version = args.explicit_version
    if version is not None and not RE_VERSION.fullmatch(version):
        print(
            f"{YELLOW}Invalid version {version!r}. Give a version such as 21"
            f" or 21.1.8.{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1
    install_clang_tools(
        version, args.tools, args.directory, args.overwrite, args.no_progress_bar
    )
    return 0


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
        help="Version to install, such as 21 or 21.1.8 (default: the newest)."
        " The static binary is installed if there is one for this version,"
        " otherwise the wheel from PyPI.",
    )
    install_p.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The directory where the clang-tools are installed. It is created if"
        " it doesn't exist, but the parent directory must exist.",
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
    from importlib.metadata import version

    print(f"clang-tools {version('clang-tools')}")


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

    return 0  # pragma: no cover (argparse only accepts the commands above)


if __name__ == "__main__":
    raise SystemExit(main())
