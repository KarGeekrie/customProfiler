#!/usr/bin/env bash

#from : R. Lenain https://github.com/code-coupling/venv-modulefile/blob/main/utils/up_version.sh

set -euo pipefail
unalias -a

current_script_dir="$( cd "$( dirname "${0}" )" &> /dev/null && pwd )"
project_root_dir="$(dirname ${current_script_dir})"

# the tag *is* the version: setuptools-scm derives it, nothing to bump in a file
version_file="${1:-}"
if [[ -z "${version_file}" ]]; then
    echo "usage: $(basename ${0}) X.Y.Z"
    echo "  the version comes from the git tag this script creates."
    echo "  current: $(git -C ${project_root_dir} describe --tags --dirty 2>/dev/null || echo none)"
    exit 1
fi
echo version_file : $version_file

########################
# Main
########################

# Check current repo status
git_status="$(git status --porcelain)"
if [[ -n "${git_status}" ]]; then
    read -p "Current repository is not clean: '${git_status}'. Do you want to continue ? (yes/[no]) " answer
    if [[ -z "${answer}" ]]||[[ "${answer}" == "n"* ]]; then
        echo "exit"
        exit 0
    fi
    echo "go"
fi

# Check input format
if ! (python3 -c "if not len('${version_file}'.split('.')) == 3: exit(1)"); then
    echo "ERROR: version format is not correct: '${version_file}', expected 'x.y.z'."
    exit 1
fi
echo "check input format OK"

# Check version number
versions_tagged=( $(git tag | grep -e '.') )
for version_tagged in ${versions_tagged[@]}; do
    if ! (python3 -c "from packaging import version; exit( 1 if version.parse('${version_file}') <= version.parse('${version_tagged}') else 0)"); then
        echo "ERROR: version is lower or equal to existing one: '${version_file}' <= ${version_tagged}."
        exit 1
    fi
done
echo "check version number OK"

# Work in venv
# if [ ! -d "${current_script_dir}/.venv_utils" ]; then
#     python3 -m venv ${current_script_dir}/.venv_utils
# fi
# . ${current_script_dir}/.venv_utils/bin/activate
pip install --upgrade pip setuptools setuptools-scm build twine

# Tag the version
git tag ${version_file}
git push origin ${version_file}

# install current version in venv
python3 -m pip install --upgrade ${project_root_dir}

cd ${project_root_dir} # && tox)

# Publish on pypi
read -p "Do you want to publish version '${version_file}' ? (yes/[no]) " answer
if [[ "${answer}" == "y"* ]]; then
    if [ -d "dist" ]; then
        rm -rf dist
    fi
    python3 -m build
    python3 -m twine upload --repository pypi dist/*
fi