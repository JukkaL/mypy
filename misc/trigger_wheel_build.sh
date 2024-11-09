#!/bin/bash -eux

# Trigger a build of mypyc compiled mypy wheels by updating the mypy
# submodule in the git repo that drives those builds.

# $WHEELS_PUSH_TOKEN is stored in Github Settings and is an API token
# for the mypy-build-bot account.

git config --global user.email "nobody"
git config --global user.name "mypy wheels autopush"

COMMIT=$(git rev-parse HEAD)
pip install -r mypy-requirements.txt
V=$(python3 -m mypy --version)
V=$(echo "$V" | cut -d" " -f2)

git clone --depth 1 https://${WHEELS_PUSH_TOKEN}@github.com/mypyc/mypy_mypyc-wheels.git build
cd build
echo $COMMIT > mypy_commit
git commit -am "Build wheels for mypy $V"
git tag v$V
# Push a tag, but no need to push the change to main
git push --tags
