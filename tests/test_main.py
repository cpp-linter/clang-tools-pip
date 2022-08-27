"""Tests that relate to the main.py module."""
import pytest
from clang_tools.main import parse_args


class Args:
    """A pseudo namespace for testing argparse.
    These class attributes are set to the CLI args default values."""

    directory: str = ""
    install: str = "13"
    overwrite: bool = False
    no_progress_bar: bool = False


@pytest.mark.parametrize("arg_name", ["install", "directory"])
@pytest.mark.parametrize("arg_value", [str(v) for v in range(7, 14)] + ["12.0.1"])
def test_arg_parser(arg_name: str, arg_value: str):
    """Test `parse_args()` using a set of fake args."""
    args = parse_args([f"--{arg_name}={arg_value}"])
    assert getattr(args, arg_name) == arg_value


def test_default_args():
    """Test the default values of CLI args"""
    args = parse_args([])
    for name, value in args.__dict__.items():
        assert getattr(Args, name) == value
