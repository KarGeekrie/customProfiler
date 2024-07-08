#!/usr/bin/env bash

#from : R. Lenain https://github.com/code-coupling/venv-modulefile/blob/main/utils/up_version.sh

set -euo pipefail
unalias -a

current_script_dir="$( cd "$( dirname "${0}" )" &> /dev/null && pwd )"
project_root_dir="$(dirname ${current_script_dir})"
version_file=$(python setup.py --version)
version_name=version_file

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
if ! (python3 -c "if not len('${version_name}'.split('.')) == 3: exit(1)"); then
    echo "ERROR: version format is not correct: '${version_name}', expected 'x.y.z'."
    exit 1
fi
echo "check input format OK"

# Check version number
versions_tagged=( $(git tag | grep -e '.') )
for version_tagged in ${versions_tagged[@]}; do
    if ! (python3 -c "from packaging import version; exit( 1 if version.parse('${version_name}') <= version.parse('${version_tagged}') else 0)"); then
        echo "ERROR: version is lower or equal to existing one: '${version_name}' <= ${version_tagged}."
        exit 1
    fi
done
echo "check version number OK"

# Work in venv
# if [ ! -d "${current_script_dir}/.venv_utils" ]; then
#     python3 -m venv ${current_script_dir}/.venv_utils
# fi
# . ${current_script_dir}/.venv_utils/bin/activate
pip install --upgrade pip setuptools tox

# Tag the version
# echo ${version_name} > ${version_file}
# git add ${version_file}
# git commit -m "Version ${version_name}"
git tag ${version_name}

# install current version in venv
python3 -m pip install --upgrade ${project_root_dir}

(cd ${project_root_dir} && tox)

# Push on origin
read -p "Do you want to push version '${version_name}' ? (yes/[no]) " answer
if [[ "${answer}" == "y"* ]]; then
    git push origin
    git push origin ${version_name}
fi

# Publish on pypi
read -p "Do you want to publish version '${version_name}' ? (yes/[no]) " answer
if [[ "${answer}" == "y"* ]]; then
    if [ -d "dist" ]; then
        rm -rf dist
    fi
    python3 -m pip install --upgrade build twine
    python3 -m build
    python3 -m twine upload --repository pypi dist/*
fi