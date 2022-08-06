from setuptools import find_packages
from setuptools import setup

with open("README.md", "r", encoding='utf-8') as file:
    long_description = file.read()


setup(
    name="clang_tools",
    description="Install clang-tools (clang-format, clang-tidy) with pip",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Peter Shen",
    author_email="xianpeng.shen@gmail.com",
    keywords=["clang", "clang-tools", "clang-extra", "clang-tidy", "clang-format"],
    license="MIT License",
    use_scm_version={"local_scheme": "no-local-version"},
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    project_urls={
        "Source": "https://github.com/cpp-linter/clang-tools-pip",
        "Tracker": "https://github.com/cpp-linter/clang-tools-pip/issues"
    },
    classifiers=[
        # https://pypi.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Build Tools",
    ],
    entry_points={
        "console_scripts": [
            "clang-tools=clang_tools.main:main"
        ]
    },
)
