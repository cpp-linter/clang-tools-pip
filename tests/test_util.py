import os
import shutil
from clang_tools.util import check_install_os, download_file, unpack_file

TEST_REPO = "https://github.com/shenxianpeng/clang-tools-pip"


def test_check_install_os():
    install_os = check_install_os()
    assert install_os in ("linux", "windos", "macosx")


def test_download_file():
    url = f"{TEST_REPO}/blob/master/README.md"
    file_name = "test_file"
    download_file(url, file_name)
    assert os.path.exists(file_name)
    os.remove(file_name)
    assert not os.path.exists(file_name)


def test_unpack_file():
    url = f"{TEST_REPO}/archive/refs/tags/v0.1.0.tar.gz"
    file_name = "test_file.tar.gz"
    download_file(url, file_name)
    status = unpack_file(file_name)
    assert status == 0
    os.remove(file_name)
    shutil.rmtree("clang-tools-pip-0.1.0")
