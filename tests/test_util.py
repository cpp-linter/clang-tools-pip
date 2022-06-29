import os
import shutil
from clang_tools.util import check_install_os, download_file, unpack_file

TEST_REPO = "https://github.com/cpp-linter/cpp-linter-action"

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
    url = f"{TEST_REPO}/archive/refs/tags/v1.4.4.tar.gz"
    file_name = "test_file.tar.gz"
    download_file(url, file_name)
    status = unpack_file(file_name)
    assert status == 0
    os.remove(file_name)
    shutil.rmtree("cpp-linter-action-1.4.4")
