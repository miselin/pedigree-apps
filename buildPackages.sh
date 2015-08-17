#!/bin/bash

# Path to prepareChroot.py
if [ "x$PATH_TO_CHROOT_SCRIPT" = "x" ]; then PATH_TO_CHROOT_SCRIPT=.; fi

pip install -r ./requirements.txt
pip install pydot  # For generating dependencies.dot

set -e
echo "Running $PATH_TO_CHROOT_SCRIPT/prepareChroot.py"
sudo PYTHONPATH="$PWD:$PYTHONPATH" "$PATH_TO_CHROOT_SCRIPT/prepareChroot.py"

target_arch="$1"
shift
echo "Now performing build proper."
python ./buildPackages.py --target=$target_arch --dryrun $*
