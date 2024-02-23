import requests
import sys

sys.path.append("../../")
from clang_tools import release_tag  # noqa E402


def get_latest_tag() -> str:
    response = requests.get(
        "https://api.github.com/repos/cpp-linter/clang-tools-static-binaries/releases/latest"
    )
    return response.json()["tag_name"]


def update_tag(current_tag, latest_tag) -> None:
    file_path = "../../clang_tools/__init__.py"
    with open(file_path) as file:
        file_content = file.read()

    updated_content = file_content.replace(current_tag, latest_tag)

    with open(file_path, "w") as file:
        file.write(updated_content)


if __name__ == "__main__":
    latest_tag = get_latest_tag()
    current_tag = release_tag

    if latest_tag != current_tag:
        update_tag(current_tag, latest_tag)

    print(latest_tag)
