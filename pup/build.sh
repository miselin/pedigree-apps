#!/usr/bin/env bash

set -e

old_working_directory=$PWD
script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_directory"

if command -v uv >/dev/null 2>&1; then
    uv build --wheel
else
    python3 -m build --wheel
fi

cd "$old_working_directory"
./runwithenv.py sh -c 'mkdir -p $APPS_BASE/pup/package_repo'
./runwithenv.py sh -c 'cp pup/dist/pup*.whl $APPS_BASE/pup/package_repo/pup.whl'
