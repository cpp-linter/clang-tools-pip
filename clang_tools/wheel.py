"""Legacy wheel module kept for backward compatibility.

Wheel installation is now handled by the unified CLI in
:mod:`clang_tools.main`. This module may be removed in a future release.

.. note::
    cpp-linter-hooks no longer maintains a hardcoded ``versions.py``.
    Tool versions are resolved dynamically from the PyPI JSON API.
"""


def _resolve_install(tool: str, version: str | None) -> str | None:  # pragma: no cover
    """Lazy import wrapper for :func:`cpp_linter_hooks.util.resolve_install`.

    Avoids a top-level import that would fail when ``cpp-linter-hooks``
    is not installed.
    """
    from cpp_linter_hooks.util import resolve_install

    return resolve_install(tool, version)
