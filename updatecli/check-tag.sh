#!/bin/bash

lastest_tag=`curl -s https://api.github.com/repos/cpp-linter/clang-tools-static-binaries/releases/latest | jq -r '.tag_name'`
current_tag=`grep -oP "^release_tag = '\K[^']+" ../clang_tools/__init__.py`

if [[ $lastest_tag = $current_tag ]]; then
    exit 0;
else
    eixt 1;
fi
