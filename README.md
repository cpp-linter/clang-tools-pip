# clang-tools

[![codecov](https://codecov.io/gh/shenxianpeng/clang-tools-pip/branch/master/graph/badge.svg?token=40G5ZOIRRR)](https://codecov.io/gh/shenxianpeng/clang-tools-pip) [![Python application](https://github.com/shenxianpeng/clang-tools-pip/actions/workflows/python-build.yml/badge.svg)](https://github.com/shenxianpeng/clang-tools-pip/actions/workflows/python-build.yml)

## Install

### Install `clang-tools` with pip

```bash
sudo pip install clang-tools
```

### Usage

```bash
sudo clang-tools --help
usage: clang-tools [-h] [-i INSTALL]

optional arguments:
  -h, --help            show this help message and exit
  -i INSTALL, --install INSTALL
                        Install clang-tools with specific version. default is 12.
```
For example 

```bash
sudo clang-tools --install 13
```

## TODO

* Modidy `clang-tools` command parameter
