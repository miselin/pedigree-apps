#!/bin/bash

# Check for a Python virtualenv for installing our dependencies and tools into.
if [ "x$VIRTUAL_ENV" = "x" ]; then
    # Standalone build creates its own virtualenv.
    if [ -e "./standalone/venv" ]; then
        source ./standalone/venv/bin/activate
    else
        echo "Please run buildPackages.sh inside a Python virtualenv." >&2
        exit 1
    fi
fi

# Path to prepareChroot.py
if [ "x$PATH_TO_CHROOT_SCRIPT" = "x" ]; then PATH_TO_CHROOT_SCRIPT=.; fi

set -e

# Install needed packages.
pip install -q -r ./requirements.txt
pip install -q pydot  # For generating dependencies.dot
pip install -q flake8  # For runtests.sh

# Make pup available for the builds.
pip install -q --upgrade pup/

# Check the installation worked (will break the build if it did not).
pup -h >/dev/null

target_arch="$1"
shift

sudo PYTHONPATH="$PWD:$PYTHONPATH" "$PATH_TO_CHROOT_SCRIPT/prepareChroot.py" "$target_arch"

LD_PRELOAD=libfakechroot.so python ./buildPackages.py --target=$target_arch $*
