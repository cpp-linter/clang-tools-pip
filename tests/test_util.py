import pytest
from clang_tools.util import check_install_os, download_file, unpack_file

TEST_REPO = "https://github.com/shenxianpeng/clang-tools-pip"


def test_check_install_os():
    install_os = check_install_os()
    assert install_os in ("linux", "windos", "macosx")

def test_unpack_file():
    file_name = "test_file.tar.gz"
    status = unpack_file(file_name)
    assert status != 0

# @pytest.fixture
# def my_download_file():
#     return [ValueError, tuple]

def test_download_file():
    ret = download_file("www.google.com", 'file.tar.gz')
    assert ret == "ValueError: unknown url type: 'www.google.com'"
    # ret = download_file("https://www.google.com", 'file.tar.gz')
    # assert tuple in ret