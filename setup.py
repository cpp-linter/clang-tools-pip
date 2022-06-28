from setuptools import setup, find_packages

setup(
    name="clang_tools",
    version = "0.0.1",
    author="Peter Shen",
    author_email="xianpeng.shen@gmail.com",
    keywords="clang clang-tools clang-extra clang-tidy clang-format",
    packages = find_packages(),
    entry_points={
        "console_scripts": [
            "clang-tools=clang_tools.main:main"
        ]
    },
)