You can override the default source for downloading **clang-tools**
by setting the following environment variables:

- `CLANG_TOOLS_REPO` – The URL of the binary repository
  (default: `https://github.com/cpp-linter/clang-tools-static-binaries`)
- `CLANG_TOOLS_TAG` – The release tag to download binaries from
  (default: `2026.06.29-ae206185`)

**Example:**

If you want to use the repository at
`https://github.com/muttleyxd/clang-tools-static-binaries`,
configure your environment like this:

```bash
export CLANG_TOOLS_REPO=https://github.com/muttleyxd/clang-tools-static-binaries
export CLANG_TOOLS_TAG=2026.06.29-ae206185  # Replace with the tag you need
```
