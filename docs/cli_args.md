---
title: clang-tools CLI
---

# `clang-tools` CLI Reference

## Usage

```text
    clang-tools [-h] {install,uninstall,version} ...
```

---

## `clang-tools install`

```text
    clang-tools install [-h] [--version VER] [-d DIR] [-f] [-b]
                           TOOL [TOOL ...]

```

### `--version`

:material-tag-outline: **v2.0.0**

Version to install (e.g. 18). When specified, binary install is tried first, falling back to wheel.

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
    clang-tools uninstall [-h] --version VER [-d DIR] TOOL [TOOL ...]

```

### `--version`

:material-tag-outline: **v0.1.0**

Version to uninstall (e.g. 18)

### `-d, --directory`

:material-tag-outline: **v0.2.0** &nbsp; Default: ``

The directory from which to uninstall the tools.

---

## `clang-tools version`

```text
    clang-tools version [-h]

```
