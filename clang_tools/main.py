"""
``clang_tools.main``
--------------------

The module containing main entrypoint function.
"""
import argparse

from .install import install_clang_tools, uninstall_clang_tools
from . import RESET_COLOR, YELLOW

def get_parser() -> argparse.ArgumentParser:
    """Get and parser to interpret CLI args."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--install",
        metavar="VERSION",
        help="Install clang-tools about a specific version.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default="",
        metavar="DIR",
        help="The directory where the clang-tools are installed.",
    )
    parser.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="Force overwriting the symlink to the installed binary. This will only "
        "overwrite an existing symlink.",
    )
    parser.add_argument(
        "-b",
        "--no-progress-bar",
        action="store_true",
        help="Do not display a progress bar for downloads.",
    )
    parser.add_argument(
        "-u",
        "--uninstall",
        metavar="VERSION",
        help="Uninstall clang-tools with specific version. "
        "This is done before any install.",
    )
    return parser


def main():
    """The main entrypoint to the CLI program."""
    parser = get_parser()
    args = parser.parse_args()
    if not args.install and not args.uninstall:
        print(
            f"{YELLOW}Nothing to do because `--install` and `--uninstall`",
            f"was not specified.{RESET_COLOR}"
        )
        parser.print_help()
    else:
        if args.uninstall:
            uninstall_clang_tools(args.uninstall, args.directory)
        if args.install:
            install_clang_tools(
                args.install, args.directory, args.overwrite, args.no_progress_bar
            )


if __name__ == "__main__":
    main()
