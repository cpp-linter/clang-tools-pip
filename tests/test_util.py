import os
from clang_tools.util import check_os, download_file, unpack_file

def test_check_os():
    system = check_os()
    assert system in ("linux", "windos", "macosx")

def test_download_file():
    url = "https://github.com/shenxianpeng/shenxianpeng/blob/master/README.md"
    file_name = "test_file"
    download_file(url, file_name)
    assert os.path.exists(file_name)
    os.remove(file_name)
    assert not os.path.exists(file_name)

def test_unpack_file():
    url = "https://github.com/shenxianpeng/shenxianpeng/archive/refs/heads/master.zip"
    file_name = "test_file.zip"
    download_file(url, file_name)
    status = unpack_file(file_name)
    assert status == 0
    os.remove(file_name)