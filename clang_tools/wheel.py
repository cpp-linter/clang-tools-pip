from argparse import ArgumentParser
from cpp_linter_hooks.util import _resolve_install


def main() -> int:
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
    args = parser.parse_args()
    path = _resolve_install(args.tool, args.version)
    if path:
        print(f"{args.tool} installed at: {path}")
        return 0
    else:
        print(f"Failed to install {args.tool} version {args.version}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
