from unittest import mock

import pytest

from clang_tools.main import main


@pytest.mark.parametrize("argv, called, response", [(['-i'], True, False), (['-d'], True, False)])
def test_main_install(argv, called, response):
    with mock.patch('sys.argv', [''] + argv):
        if called and not response:
            with pytest.raises(SystemExit):
                main()
