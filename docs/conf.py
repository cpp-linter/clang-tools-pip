# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
from pathlib import Path
import io
from docutils.nodes import Node
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from clang_tools.main import get_parser

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = "clang-tools"
copyright = "2022, cpp-linter team"
author = "cpp-linter team"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_immaterial",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_immaterial"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_logo = "_static/logo.png"
html_favicon = "_static/new_favicon.ico"
html_css_files = ["extra_css.css"]
html_title = "clang-tools installer"

html_theme_options = {
    "repo_url": "https://github.com/cpp-linter/clang-tools-pip",
    "repo_name": "clang-tools",
    "repo_type": "github",
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "indigo",
            "accent": "cyan",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            }
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "indigo",
            "accent": "cyan",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            }
        },
    ],
    "features": [
        "navigation.top",
        "navigation.tabs",
        "navigation.tabs.sticky",
        "toc.sticky",
        "toc.follow",
        "search.share",
    ]
}

object_description_options = [
    ("py:parameter", dict(include_in_toc=False)),
]


# -- Parse CLI args from `-h` output -------------------------------------


def parse_cli_option(env: BuildEnvironment, sig: str, sig_node: Node):
    """parse the given signature of a CLI option and
    return the docutil nodes accordingly."""
    opt_names = sig.split(", ")
    sig_node["is_multiline"] = True
    for i, opt_name in enumerate(opt_names):
        name = addnodes.desc_signature_line("", "--" if i else opt_name)
        if not i:
            name["add_permalink"] = True
        else:
            name += addnodes.desc_name(opt_name, opt_name.lstrip("-"))
        sig_node += name
    # print(sig_node.pformat())
    return opt_names[-1].lstrip("-")


def setup(app: Sphinx):
    """Generate a doc from the executable script's ``--help`` output."""
    app.add_object_type(
        "cli-opt",
        "cli-opt",
        objname="Command Line Interface option",
        indextemplate="pair: %s; Command Line Interface option",
        parse_node=parse_cli_option,
    )

    with io.StringIO() as help_out:
        get_parser().print_help(help_out)
        output = help_out.getvalue()
    first_line = re.search(r"^options:\s*\n", output, re.MULTILINE)
    if first_line is None:
        raise OSError("unrecognized output from `clang-tools -h`")
    output = output[first_line.end(0) :]
    doc = "Command Line Interface Options\n==============================\n\n"
    cli_opt_name = re.compile(r"^\s*(\-\w)?\s?[A-Z_]*,\s(\-\-.*?)(?:\s|$)")
    for line in output.splitlines():
        match = cli_opt_name.search(line)
        if match is not None:
            print(match.groups())
            doc += "\n.. cli-opt:: " + ", ".join(match.groups()) + "\n\n"
        doc += line + "\n"
    cli_doc = Path(app.srcdir, "cli_args.rst")
    cli_doc.unlink(missing_ok=True)
    cli_doc.write_text(doc, encoding="utf-8")
