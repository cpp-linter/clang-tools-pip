"""Tests that relate to the main.py module."""
from typing import Optional, List
from argparse import ArgumentParser
import pytest
from clang_tools.main import get_parser


class Args:
    """A pseudo namespace for testing argparse.
    These class attributes are set to the CLI args default values."""

    directory: str = ""
    install: Optional[str] = None
    overwrite: bool = False
    no_progress_bar: bool = False
    uninstall: Optional[str] = None
    tool: List[str] = ["clang-format", "clang-tidy"]


@pytest.fixture
def parser() -> ArgumentParser:
    """get the arg parser for the tests in this module."""
    return get_parser()


@pytest.mark.parametrize("arg_name", ["install", "directory", "uninstall"])
@pytest.mark.parametrize("arg_value", [str(v) for v in range(7, 17)] + ["12.0.1"])
def test_arg_parser(arg_name: str, arg_value: str, parser: ArgumentParser):
    """Test CLI arg parsing using a set of fake args."""
    args = parser.parse_args([f"--{arg_name}={arg_value}"])
    assert getattr(args, arg_name) == arg_value


@pytest.mark.parametrize("switch_name", ["overwrite", "no-progress-bar"])
def test_cli_switch(switch_name: str, parser: ArgumentParser):
    """Test the CLI switches/flags"""
    args = parser.parse_args([f"--{switch_name}"])
    assert getattr(args, switch_name.replace("-", "_"))


def test_default_args(parser: ArgumentParser):
    """Test the default values of CLI args"""
    args = parser.parse_args([])
    for name, value in args.__dict__.items():
        assert getattr(Args, name) == value
