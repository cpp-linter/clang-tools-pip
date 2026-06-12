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
from . import RESET_COLOR, YELLOW, MIN_VERSION, MAX_VERSION
from .util import Version


def _is_version_like(target: str) -> bool:
    """Check if *target* looks like a version number (e.g. ``"18"``, ``"18.1"``).
    """
    try:
        parts = target.split(".")
        for p in parts:
            int(p)
        return True
    except ValueError:
        return False


#: Known tool names supported by wheel installs
WHEEL_TOOLS = {"clang-format", "clang-tidy"}


def _wheel_install(tools: list[str], version: Optional[str]) -> int:
    """Install tool(s) via wheel (cpp_linter_hooks).

    :returns: exit code (0 on success, 1 on failure).
    """
    from cpp_linter_hooks.util import resolve_install  # lazy import

    ok = True
    for tool in tools:
        path = resolve_install(tool, version)
        version_str = f" version {version}" if version else " latest version"
        if path:
            print(f"{tool}{version_str} installed at: {path}")
        else:
            print(f"Failed to install {tool}{version_str}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


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
        help="Force wheel installation via cpp-linter-hooks",
    )
    install_p.add_argument(
        "--version",
        dest="explicit_version",
        default=None,
        metavar="VER",
        help="Explicit version for wheel install (when target is a tool name)",
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

    # ---- No subcommand → nothing to do ----------------------------------
    if args.command is None:
        print(
            f"{YELLOW}Nothing to do. Use 'install' or 'uninstall'"
            f" subcommand.{RESET_COLOR}",
            file=sys.stderr,
        )
        parser.print_help()
        return 0

    # ---- ``uninstall`` subcommand ------------------------------------
    if args.command == "uninstall":
        uninstall_clang_tools(args.version, args.tool, args.directory)
        return 0

    # ---- ``install`` subcommand --------------------------------------
    if args.command == "install":
        target: str = args.target
        binary: bool = args.binary
        wheel: bool = args.wheel

        # safety: --binary and --wheel are mutually exclusive
        if binary and wheel:
            print(
                f"{YELLOW}Error: --binary and --wheel are mutually"
                f" exclusive{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1

        # ---- Case: --wheel (target may be tool name or version) -----
        if wheel:
            if _is_version_like(target):
                # ``clang-tools install 18 --wheel``
                return _wheel_install(args.tool, target)
            else:
                # ``clang-tools install clang-format --wheel``
                if target not in WHEEL_TOOLS:
                    print(
                        f"{YELLOW}Error: '{target}' is not available as a"
                        f" wheel. Supported: "
                        f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
                        file=sys.stderr,
                    )
                    return 1
                return _wheel_install([target], args.explicit_version)

        # ---- Case: --binary (target must be a version) --------------
        if binary:
            if not _is_version_like(target):
                print(
                    f"{YELLOW}Error: --binary requires a version number"
                    f" (got '{target}'){RESET_COLOR}",
                    file=sys.stderr,
                )
                return 1
            version = Version(target)
            if version.info != (0, 0, 0):
                install_clang_tools(
                    version,
                    args.tool,
                    args.directory,
                    args.overwrite,
                    args.no_progress_bar,
                )
                return 0
            print(
                f"{YELLOW}The version specified is not a semantic"
                f" specification{RESET_COLOR}",
                file=sys.stderr,
            )
            return 1

        # ---- Auto-detect (no --binary or --wheel flag) --------------
        if _is_version_like(target):
            version = Version(target)
            if version.info != (0, 0, 0):
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
                except Exception as exc:
                    print(
                        f"{YELLOW}Binary install failed"
                        f" ({exc}), falling back to"
                        f" wheel...{RESET_COLOR}",
                        file=sys.stderr,
                    )
                # fallback to wheel
                return _wheel_install(args.tool, target)
            else:
                print(
                    f"{YELLOW}The version specified is not a semantic"
                    f" specification{RESET_COLOR}",
                    file=sys.stderr,
                )
                return 1
        else:
            # target is a tool name → install via wheel
            if target not in WHEEL_TOOLS:
                print(
                    f"{YELLOW}Unknown target '{target}'. Expected a"
                    f" version number or one of: "
                    f"{', '.join(sorted(WHEEL_TOOLS))}{RESET_COLOR}",
                    file=sys.stderr,
                )
                return 1
            return _wheel_install([target], args.explicit_version)

    return 0  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
