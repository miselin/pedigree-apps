#!/bin/bash

if [ "x$VIRTUAL_ENV" = "x" ]; then
    echo "Please run buildPackages.sh inside a Python virtualenv." >&2
    exit 1
fi

# Path to prepareChroot.py
if [ "x$PATH_TO_CHROOT_SCRIPT" = "x" ]; then PATH_TO_CHROOT_SCRIPT=.; fi

set -e

# Install needed packages.
pip install -r ./requirements.txt
pip install pydot  # For generating dependencies.dot

# Make pup available for the builds.
pip install --upgrade pup/

# Check the installation worked (will break the build if it did not).
pup -h >/dev/null

echo "Running $PATH_TO_CHROOT_SCRIPT/prepareChroot.py"
sudo PYTHONPATH="$PWD:$PYTHONPATH" "$PATH_TO_CHROOT_SCRIPT/prepareChroot.py"

target_arch="$1"
shift
echo "Now performing build proper."
LD_PRELOAD=libfakechroot.so python ./buildPackages.py --target=$target_arch $*
