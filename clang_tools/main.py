import argparse
from clang_tools.install import install_clang_tools

def main() -> int:
    parser = argparse.ArgumentParser(prog='clang-tools')
    # parser.add_argument(
    #     "-b",
    #     "--build",
    #     default="false",
    #     help="Build clang-tools.",
    # )
    parser.add_argument(
        "-i",
        "--install",
        default="12",
        help="Install clang-tools with specific version. default is 12.",
    )
    # parser.add_argument(
    #     "-v",
    #     "--version", 
    #     default="12",
    #     help="The version of clang-tools. default is 12.",
    # )
    # parser.add_argument(
    #     "-d",
    #     "--directory", 
    #     default="/usr/bin/",
    #     help="The directory where is the clang-tools install.", 
    # )
    args = parser.parse_args()

    install_version = args.install
    # install_dir = args.directory

    if install_version:
        install_clang_tools(install_version)

    # if build:
        # TODO

if __name__ == '__main__':
    raise SystemExit(main())
