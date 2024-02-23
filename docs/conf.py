# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path
from sphinx.application import Sphinx
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

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# add emphasis to metavar of CLI options
# option_emphasise_placeholders = True

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
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "indigo",
            "accent": "cyan",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "indigo",
            "accent": "cyan",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
    ],
    "features": [
        "navigation.top",
        "navigation.tabs",
        "navigation.tabs.sticky",
        "toc.sticky",
        "toc.follow",
        "search.share",
    ],
}

object_description_options = [
    ("py:parameter", dict(include_in_toc=False)),
    ("std:option", dict(include_fields_in_toc=False)),
]


# -- Parse CLI args from `-h` output -------------------------------------
# pylint: disable=protected-access


def setup(app: Sphinx):
    """Generate a doc from the executable script's ``--help`` output."""
    parser = get_parser()
    # print(parser.format_help())
    formatter = parser._get_formatter()
    doc = "Command Line Interface Options\n==============================\n\n"
    for arg in parser._actions:
        doc += f"\n.. option:: {formatter._format_action_invocation(arg)}\n\n"
        if arg.default != "==SUPPRESS==":
            doc += f"    :Default: ``{repr(arg.default)}``\n\n"
        description = (
            "" if arg.help is None else "    %s\n" % (arg.help.replace("\n", "\n    "))
        )
        doc += description
    cli_doc = Path(app.srcdir, "cli_args.rst")
    cli_doc.write_text(doc, encoding="utf-8")
