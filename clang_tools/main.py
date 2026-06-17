"""
``clang_tools.main``
--------------------

The module containing the unified main entrypoint function.
Supports both binary (static build) and wheel-based installation
via a single ``clang-tools`` command.
"""

import argparse
import sys
from typing import Optional

from .install import install_clang_tools, uninstall_clang_tools
from . import RESET_COLOR, YELLOW
from .util import Version


def _is_version_like(target: str) -> bool:
    """Check if *target* looks like a version number (e.g. ``"18"``, ``"18.1"``)."""
    try:
        parts = target.split(".")
        for p in parts:
            int(p)
        return True
    except ValueError:
        return False


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


def _validate_wheel_tool(target: str) -> bool:
    """Print an error and return `False` if *target* is not a wheel tool."""
    if target not in WHEEL_TOOLS:
        print(
            f"{YELLOW}Error: '{target}' is not available as a"
            f" wheel. Supported: "
            f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
            file=sys.stderr,
        )
        return False
    return True


def _handle_wheel(args: argparse.Namespace) -> int:
    """Handle ``install --wheel`` subcommand."""
    target: str = args.target
    if _is_version_like(target):
        return _wheel_install(args.tool, target)
    if not _validate_wheel_tool(target):
        return 1
    return _wheel_install([target], args.explicit_version)


def _handle_binary(args: argparse.Namespace) -> int:
    """Handle ``install --binary`` subcommand.

    Supports two argument styles (consistent with ``--wheel``):

    * ``clang-tools install <version> --tool <tool> --binary``
    * ``clang-tools install <tool> --version <VER> --binary``
    """
    target: str = args.target
    if _is_version_like(target):
        version = Version(target)
        tools = args.tool
    else:
        # target is a tool name — use --version for the version number
        if args.explicit_version is None:
            print(
                f"{YELLOW}Error: --binary requires a version number"
                f" (got '{target}'). "
                f"Use e.g. 'clang-tools install {target}"
                f" --version <VER> --binary'{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1
        version = Version(args.explicit_version)
        tools = [target]
    if version.info == (0, 0, 0):
        print(
            f"{YELLOW}The version specified is not a semantic"
            f" specification{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1
    install_clang_tools(
        version,
        tools,
        args.directory,
        args.overwrite,
        args.no_progress_bar,
    )
    return 0


def _handle_auto_detect(args: argparse.Namespace) -> int:
    """Handle ``install`` without --binary/--wheel (auto-detect mode)."""
    target: str = args.target
    if not _is_version_like(target):
        if target not in WHEEL_TOOLS:
            print(
                f"{YELLOW}Unknown target '{target}'. Expected a"
                f" version number or one of: "
                f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1
        return _wheel_install([target], args.explicit_version)

    version = Version(target)
    if version.info == (0, 0, 0):
        print(
            f"{YELLOW}The version specified is not a semantic"
            f" specification{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1

    # try binary first, fall back to wheel
    try:
        install_clang_tools(
            version,
            args.tool,
            args.directory,
            args.overwrite,
            args.no_progress_bar,
        )
        return 0
    except (OSError, ValueError) as exc:
        print(
            f"{YELLOW}Binary install failed"
            f" ({exc}), falling back to"
            f" wheel...{RESET_COLOR}",
            file=sys.stderr,
        )
    return _wheel_install(args.tool, target)


def _handle_install(args: argparse.Namespace) -> int:
    """Dispatch ``install`` subcommand based on flags."""
    if args.binary and args.wheel:
        print(
            f"{YELLOW}Error: --binary and --wheel are mutually exclusive{RESET_COLOR}",
            file=sys.stderr,
        )
        return 1

    if args.wheel:
        return _handle_wheel(args)
    if args.binary:
        return _handle_binary(args)
    return _handle_auto_detect(args)


def get_parser() -> argparse.ArgumentParser:
    """Get a parser to interpret CLI args (unified entry point)."""
    parser = argparse.ArgumentParser(
        description="Install and manage clang-tools (clang-format, clang-tidy, etc.)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- ``clang-tools install <target>`` ---------------------------------
    install_p = subparsers.add_parser("install", help="Install clang-tools")
    install_p.add_argument(
        "target",
        help="Version number (e.g. 18) or tool name (e.g. clang-format)",
    )
    install_p.add_argument(
        "--binary",
        action="store_true",
        help="Force binary (static build) installation",
    )
    install_p.add_argument(
        "--wheel",
        action="store_true",
        help="Force wheel installation (resolves versions from PyPI)",
    )
    install_p.add_argument(
        "--version",
        dest="explicit_version",
        default=None,
        metavar="VER",
        help="Explicit version (when target is a tool name, for both --wheel and --binary)",
    )
    install_p.add_argument(
        "-t",
        "--tool",
        nargs="+",
        default=["clang-format", "clang-tidy"],
        metavar="TOOL",
        help="Specify which tool(s) to install.",
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

    # --- ``clang-tools uninstall <version>`` ------------------------------
    uninstall_p = subparsers.add_parser("uninstall", help="Uninstall clang-tools")
    uninstall_p.add_argument("version", help="Version to uninstall")
    uninstall_p.add_argument(
        "-t",
        "--tool",
        nargs="+",
        default=["clang-format", "clang-tidy"],
        metavar="TOOL",
        help="Specify which tool(s) to uninstall.",
    )
    uninstall_p.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The directory from which to uninstall the tools.",
    )

    return parser


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

    if args.command == "uninstall":
        uninstall_clang_tools(args.tool, args.version, args.directory)
        return 0

    if args.command == "install":
        return _handle_install(args)

    return 0  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
