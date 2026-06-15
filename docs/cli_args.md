---
title: clang-tools CLI
---

# `clang-tools` CLI Reference

## Usage

```text
    clang-tools [-h] {install,uninstall} ...
```

---

## `clang-tools install`

```text
    clang-tools install [-h] [--binary] [--wheel] [--version VER]
                           [-t TOOL [TOOL ...]] [-d DIR] [-f] [-b]
                           target

```

### `--binary`

:material-tag-outline: **v1.0.0** &nbsp; Default: `False` &nbsp; Accepts no value

Force binary (static build) installation

### `--wheel`

:material-tag-outline: **v1.0.0** &nbsp; Default: `False` &nbsp; Accepts no value

Force wheel installation (resolves versions from PyPI)

### `--version`

:material-tag-outline: **v1.0.0**

Explicit version for wheel install (when target is a tool name)

### `-t, --tool`

:material-tag-outline: **v0.11.0** &nbsp; Default: `clang-format clang-tidy`

Specify which tool(s) to install.

### `-d, --directory`

:material-tag-outline: **v0.2.0** &nbsp; Default: ``

The directory where the clang-tools are installed.

### `-f, --overwrite`

:material-tag-outline: **v0.3.0** &nbsp; Default: `False` &nbsp; Accepts no value

Force overwriting the symlink to the installed binary.

### `-b, --no-progress-bar`

:material-tag-outline: **v0.5.0** &nbsp; Default: `False` &nbsp; Accepts no value

Do not display a progress bar for downloads.

---

## `clang-tools uninstall`

```text
    clang-tools uninstall [-h] [-t TOOL [TOOL ...]] [-d DIR] version

```

### `-t, --tool`

:material-tag-outline: **v0.11.0** &nbsp; Default: `clang-format clang-tidy`

Specify which tool(s) to uninstall.

### `-d, --directory`

:material-tag-outline: **v0.2.0** &nbsp; Default: ``

The directory from which to uninstall the tools.
