#!/bin/bash

new_release_tag=$1
file_path="clang_tools/__init__.py"
regex="^release_tag = 'master-\\w*'"

script_dir=`pwd`
cd "$script_dir/.."

# Check if the file exists
if [ -f "$file_path" ]; then
  # Use sed to replace the regex with the desired string
  sed -i "s/$regex/release_tag = '$new_release_tag'/g" "$file_path"
  echo "release_tag updated successfully."
else
  echo "File $file_path not found."
fi

# Return to the original directory
cd - >/dev/null
