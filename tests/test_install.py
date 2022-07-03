import pytest
from clang_tools.install import check_install_os
from clang_tools.install import clang_format_exist
from clang_tools.install import clang_tidy_exist
from clang_tools.install import clang_tools_binary_url


def test_clang_format_exist():
    ret = clang_format_exist('1000')
    assert ret == False


def test_clang_tidy_exist():
    ret = clang_tidy_exist('1000')
    assert ret == False

def test_clang_tools_binary_url():
    tools = ['clang-format', 'clang-tidy']
    version = 12
    os = check_install_os()
    for tool in tools:
        ret = clang_tools_binary_url(tool, version)
        if os == 'windows':
            assert(f"{tool}-{version}_{os}-amd64.exe" in ret)
        else:
            assert(f"{tool}-{version}_{os}-amd64" in ret)

def 