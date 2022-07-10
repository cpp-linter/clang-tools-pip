from unittest import mock

from clang_tools.util import check_install_os
from clang_tools.util import download_file
from clang_tools.util import unpack_file


def test_check_install_os():
    install_os = check_install_os()
    assert install_os in ("linux", "windos", "macosx")


@mock.patch('clang_tools.util.urllib.request.urlretrieve')
def test_fail_download_file(mock_request):
    mock_result = mock.MagicMock()
    attrs = {'mock_result.return_value': 'file.tar.gz'}
    mock_result.configure_mock(**attrs)
    mock_request.return_value = mock_result
    file_name = download_file('https://www.google.com', 'file.tar.gz')
    assert file_name is None


@mock.patch('clang_tools.util.subprocess.run')
def test_unpack_file(mock_run):
    mock_stdout = mock.Mock()
    mock_stdout.configure_mock(**{"returncode": '0'})
    mock_run.return_value = mock_stdout
    result = unpack_file('file.tar.gz')
    assert result == '0'
