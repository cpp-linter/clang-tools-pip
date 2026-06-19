"""Generate CLI argument documentation pages for MkDocs.

This script is used as a `gen-files` plugin to auto-generate
the `cli_args.md` page from argparse.
"""

from io import StringIO
import argparse
import mkdocs_gen_files
from clang_tools.main import get_parser

REQUIRED_VERSIONS = {
    "0.1.0": ["command", "version"],
    "0.2.0": ["directory"],
    "0.3.0": ["overwrite"],
    "0.5.0": ["no_progress_bar"],
    "2.0.0": ["tools", "explicit_version", "backend"],
}


def _action_doc(arg) -> str:
    """Generate markdown for a single argparse action."""
    aliases = arg.option_strings
    if not aliases or arg.default == "==SUPPRESS==":
        return ""
    if arg.help is None:
        msg = f"Argument {aliases[0] if aliases else arg.dest} missing help text"
        raise ValueError(msg)

    lines = [f"### `{', '.join(aliases)}`\n"]

    req_ver = next(
        (ver for ver, names in REQUIRED_VERSIONS.items() if arg.dest in names),
        "0.1.0",
    )
    badges = [f":material-tag-outline: **v{req_ver}**"]

    if arg.default is not None:
        default = (
            " ".join(arg.default) if isinstance(arg.default, list) else arg.default
        )
        badges.append(f"Default: `{default}`")
    if arg.default is False and arg.const is True:
        badges.append("Accepts no value")

    lines.append(" &nbsp; ".join(badges) + "\n")
    lines.append(arg.help + "\n")
    return "\n".join(lines)


def _write_cli_doc(parser, prog_name: str) -> str:
    """Generate markdown documentation from an argparse parser."""
    lines = []
    lines.append(f"---\ntitle: {prog_name} CLI\n---\n")
    lines.append(f"# `{prog_name}` CLI Reference\n")

    # Top-level usage
    lines.append("## Usage\n")
    lines.append("```text")
    parser.prog = prog_name
    str_buf = StringIO()
    parser.print_usage(str_buf)
    usage = str_buf.getvalue()
    start = usage.find(parser.prog)
    for line in usage.splitlines():
        lines.append(f"    {line[start:]}")
    lines.append("```\n")

    # Top-level options (subcommands placeholder)
    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            continue
        doc = _action_doc(action)
        if doc:
            lines.append(doc)

    # Subcommand details
    if subparsers_action is not None:
        for name, sub in subparsers_action.choices.items():
            lines.append(f"---\n\n## `{prog_name} {name}`\n")
            lines.append("```text")
            sub.prog = f"{prog_name} {name}"
            str_buf = StringIO()
            sub.print_usage(str_buf)
            sub_usage = str_buf.getvalue()
            sub_start = sub_usage.find(sub.prog)
            lines.append(f"    {sub_usage[sub_start:]}")
            lines.append("```\n")

            for action in sub._actions:
                if not action.option_strings or action.default == "==SUPPRESS==":
                    continue
                doc = _action_doc(action)
                if doc:
                    lines.append(doc)

    return "\n".join(lines)


def _generate(filename: str, content: str) -> None:
    with mkdocs_gen_files.open(filename, "w") as f:
        print(content, file=f)
    mkdocs_gen_files.set_edit_path(filename, "gen_cli_docs.py")


_generate("cli_args.md", _write_cli_doc(get_parser(), "clang-tools"))
