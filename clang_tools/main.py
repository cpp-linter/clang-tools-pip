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

    # Show the installed tools, or the versions that can be installed
    clang-tools list
    clang-tools list --available
"""

import argparse
import json
import sys

from . import RESET_COLOR, YELLOW
from .install import (
    install_clang_tools,
    install_dir_name,
    platform_name,
    uninstall_clang_tools,
)
from .listing import available_tools, installed_tools
from .util import RE_VERSION, PyPIFallback


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


def _handle_list(args: argparse.Namespace) -> int:
    """Handle the ``list`` subcommand.

    :returns: exit code (0 on success, 1 on failure).
    """
    if args.available:
        try:
            available = available_tools()
        except PyPIFallback as exc:
            print(f"{YELLOW}{exc}{RESET_COLOR}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(available, indent=2))
            return 0
        print(f"Static binaries for {platform_name()}:")
        for entry in available:
            print(f"  {entry['version']:<9} {', '.join(entry['tools'])}")
        return 0
    installed = installed_tools(args.directory)
    if args.json:
        print(json.dumps([tool._asdict() for tool in installed], indent=2))
        return 0
    install_dir = install_dir_name(args.directory)
    if not installed:
        print(f"No clang tools in {install_dir}")
        return 0
    print(f"Tools in {install_dir}:")
    name_width = max(len(tool.tool) for tool in installed)
    version_width = max(len(tool.version) for tool in installed)
    for tool in installed:
        print(
            f"  {tool.tool:<{name_width}}  {tool.version:<{version_width}}"
            f"  {tool.source:<6}  {'default' if tool.default else '':<7}  {tool.path}"
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

    # --- ``clang-tools list`` ---------------------------------------------
    list_p = subparsers.add_parser(
        "list", help="List the installed tools, or the versions that can be installed"
    )
    list_p.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The install directory to look in.",
    )
    list_p.add_argument(
        "-a",
        "--available",
        action="store_true",
        help="List the static binaries that can be installed on this platform,"
        " instead of the installed tools.",
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        help="Print the list as JSON.",
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
            f"{YELLOW}Nothing to do. Use 'install', 'uninstall' or 'list'"
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

    if args.command == "list":
        return _handle_list(args)

    if args.command == "version":
        _print_version()
        return 0

    return 0  # pragma: no cover (argparse only accepts the commands above)


if __name__ == "__main__":
    raise SystemExit(main())
