By default, **clang-tools** looks up each static binary, and the SHA512 checksum it must match,
in the [index](https://cpp-linter.github.io/clang-tools-static-binaries/index.json) of
[clang-tools-static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries).
Each LLVM version there has its own release, so a new LLVM version or patch release is
available without upgrading this package.

You can change where the binaries come from with these environment variables:

- `CLANG_TOOLS_INDEX_URL` – The URL of the index
  (default: `https://cpp-linter.github.io/clang-tools-static-binaries/index.json`)
- `CLANG_TOOLS_TAG` – Download every binary from this one release instead of using the index.
  The release must hold a `SHA512SUMS` file and binaries named like
  `clang-format-21_linux-amd64`.
- `CLANG_TOOLS_REPO` – The repository of the release named by `CLANG_TOOLS_TAG`
  (default: `https://github.com/cpp-linter/clang-tools-static-binaries`)

**Examples:**

To keep using the last release that held every version:

```bash
export CLANG_TOOLS_TAG=2026.09.01-5fb8802d
```

To use a fork, such as `https://github.com/muttleyxd/clang-tools-static-binaries`:

```bash
export CLANG_TOOLS_REPO=https://github.com/muttleyxd/clang-tools-static-binaries
export CLANG_TOOLS_TAG=2026.07.02-e6fa8f6a  # Replace with the tag you need
```
