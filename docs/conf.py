# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from argparse import _StoreTrueAction
from io import StringIO
from pathlib import Path
import time
from typing import Optional
import docutils
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxRole
from sphinx_immaterial.inline_icons import load_svg_into_builder_env
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

year = time.strftime("%Y", time.gmtime())
project = "clang-tools"
copyright = f"{year}, cpp-linter team"
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


class CliBadge(SphinxRole):
    badge_type: str
    badge_icon: Optional[str] = None
    href: Optional[str] = None
    href_title: Optional[str] = None

    def run(self):
        is_linked = ""
        if self.href is not None and self.href_title is not None:
            is_linked = (
                f'<a href="{self.href}{self.text}" ' + f'title="{self.href_title}">'
            )
        head = '<span class="mdx-badge__icon">'
        if not self.badge_icon:
            head += self.badge_type.title()
        else:
            head += is_linked
            head += (
                f'<span class="md-icon si-icon-inline {self.badge_icon}"></span></a>'
            )
        head += "</span>"
        header = docutils.nodes.raw(
            self.rawtext,
            f'<span class="mdx-badge">{head}<span class="mdx-badge__text">'
            + is_linked
            + (self.text if self.badge_type in ["version", "switch"] else ""),
            format="html",
        )
        if self.badge_type not in ["version", "switch"]:
            code, sys_msgs = docutils.parsers.rst.roles.code_role(
                role="code",
                rawtext=self.rawtext,
                text=self.text,
                lineno=self.lineno,
                inliner=self.inliner,
                options={"language": "text", "classes": ["highlight"]},
                content=self.content,
            )
        else:
            code, sys_msgs = ([], [])
        tail = "</span></span>"
        if self.href is not None and self.href_title is not None:
            tail = "</a>" + tail
        trailer = docutils.nodes.raw(self.rawtext, tail, format="html")
        return ([header, *code, trailer], sys_msgs)


class CliBadgeVersion(CliBadge):
    badge_type = "version"
    href = "https://github.com/cpp-linter/clang-tools-pip/releases/v"
    href_title = "Minimum Version"

    def run(self):
        self.badge_icon = load_svg_into_builder_env(
            self.env.app.builder, "material/tag-outline"
        )
        return super().run()


class CliBadgeDefault(CliBadge):
    badge_type = "Default"


class CliBadgeSwitch(CliBadge):
    badge_type = "switch"

    def run(self):
        self.badge_icon = load_svg_into_builder_env(
            self.env.app.builder, "material/toggle-switch"
        )
        return super().run()


REQUIRED_VERSIONS = {
    "0.1.0": ["install"],
    "0.2.0": ["directory"],
    "0.3.0": ["overwrite"],
    "0.5.0": ["no_progress_bar", "uninstall"],
    "0.11.0": ["tool"],
}


def setup(app: Sphinx):
    """Generate a doc from the executable script's ``--help`` output."""
    app.add_role("badge-version", CliBadgeVersion())
    app.add_role("badge-default", CliBadgeDefault())
    app.add_role("badge-switch", CliBadgeSwitch())

    cli_doc = Path(app.srcdir, "cli_args.rst")
    with open(cli_doc, mode="w") as doc:
        doc.write("Command Line Interface Options\n==============================\n\n")
        parser = get_parser()
        doc.write(".. code-block:: text\n    :caption: Usage\n    :class: no-copy\n\n")
        parser.prog = "clang-tools"
        str_buf = StringIO()
        parser.print_usage(str_buf)
        usage = str_buf.getvalue()
        start = usage.find(parser.prog)
        for line in usage.splitlines():
            doc.write(f"    {line[start:]}\n")

        args = parser._optionals._actions
        for arg in args:
            aliases = arg.option_strings
            if not aliases or arg.default == "==SUPPRESS==":
                continue
            assert arg.help is not None
            doc.write("\n.. std:option:: " + ", ".join(aliases) + "\n")
            req_ver = "0.1.0"
            for ver, names in REQUIRED_VERSIONS.items():
                if arg.dest in names:
                    req_ver = ver
                    break
            doc.write(f"\n    :badge-version:`{req_ver}` ")
            if arg.default:
                default = arg.default
                if isinstance(arg.default, list):
                    default = " ".join(arg.default)
                doc.write(f":badge-default:`{default}` ")
            if isinstance(arg, _StoreTrueAction):
                doc.write(":badge-switch:`Accepts no value` ")
            doc.write("\n\n    ")
            doc.write("\n    ".join(arg.help.splitlines()) + "\n")
