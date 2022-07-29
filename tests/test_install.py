import pytest

from clang_tools.install import check_install_os
from clang_tools.install import clang_format_exist
from clang_tools.install import clang_tidy_exist
from clang_tools.install import clang_tools_binary_url


@pytest.mark.parametrize(('version', 'expected'), (('', True), ('100', False)))
def test_clang_tools_exist(version, expected):
    assert clang_format_exist(version) == expected
    assert clang_tidy_exist(version) == expected


def test_clang_tools_binary_url():
    tools = ['clang-format', 'clang-tidy']
    version = 12
    os = check_install_os()
    for tool in tools:
        ret = clang_tools_binary_url(tool, version)
        assert(f"{tool}-{version}_{os}-amd64" in ret)
