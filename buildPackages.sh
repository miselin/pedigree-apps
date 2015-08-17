#!/bin/bash

# Path to prepareChroot.py
if [ "x$PATH_TO_CHROOT_SCRIPT" = "x" ]; then PATH_TO_CHROOT_SCRIPT=.; fi

set -e
sudo PYTHONPATH=$PWD:$PYTHONPATH $PATH_TO_CHROOT/prepareChroot.py

python ./buildPackages.py --target=$1 --dryrun
