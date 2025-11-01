from argparse import ArgumentParser
from cpp_linter_hooks.util import resolve_install


def get_parser() -> ArgumentParser:
    """Get a parser to interpret CLI args."""
    parser = ArgumentParser(description="Install specified clang tool wheel")
    parser.add_argument(
        "--tool",
        default="clang-format",
        choices=["clang-format", "clang-tidy"],
        help="Tool to install (clang-format or clang-tidy)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version to install (e.g., 21 or 21.1.2). Defaults to latest compatible version.",
    )
    return parser


def main() -> int:
    parser = get_parser()
    args = parser.parse_args()
    path = resolve_install(args.tool, args.version)
    version_str = f" version {args.version}" if args.version else " latest version"
    if path:
        print(f"{args.tool}{version_str} installed at: {path}")
        return 0
    else:
        print(f"Failed to install {args.tool}{version_str}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
