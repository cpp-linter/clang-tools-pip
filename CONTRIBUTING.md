# Contributing

Thank you for investing your time in contributing to this project! ✨.

## Make Changes

When you're finished with the changes, create a pull request, also known as a PR.

* Please helps reviewers understand the purpose of your pull request.
* Don't forget to link PR to issue if you are solving one.
* If you run into any merge issues, please resolve merge conflicts and other issues.

## Development

### Build

Install `clang-tools` from source code

```bash
$ git clone git@github.com:cpp-linter/clang-tools-pip.git
$ cd clang-tools-pip
$ pip install -e .
# Install clang-tools version 13
$ clang-tools install 13
```

### Test

```bash
# run test
$ pytest
# run test with code covarege
$ coverage run -m pytest
```

## Code format

```bash
# check code format with flake8
$ flake8 .
```
