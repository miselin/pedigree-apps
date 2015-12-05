#!/bin/bash

# Standalone pedigree-apps prepare - builds a local Pedigree build and then
# writes out a local configuration that uses that build directly. This allows
# the pedigree-apps build to be completely self-contained.

# TODO(miselin): assumes running on a build slave
# TODO(miselin): assumes Debian as the host system, and an x86_64 target.

# Abort the build immediately if anything goes wrong.
set -e

UNPRIV_UID=$(id -u buildbot)
UNPRIV_GID=$(id -g buildbot)

LOCALDIR="$PWD"

# Make sure we're in the pedigree-apps root.
if [ ! -e "./buildPackages.py" ]; then
    echo "Must be run in pedigree-apps root directory." 1>&2
    exit 1
fi

mkdir -p standalone && cd standalone

# Grab Pedigree first.
if [ ! -e "pedigree" ]; then
    git clone --depth 1 https://github.com/miselin/pedigree.git
fi

# Go ahead and build it.
cd pedigree
git pull
./easy_build_x64.sh debian build_images=0
cd ..

# Create our local configuration, ready to ship.
cd ..
cat >local_environment.py <<EOF

import functools

from support.util import expand


def modify_environment(env):
    _expand = functools.partial(expand, env)
    env['PEDIGREE_BASE'] = _expand('$LOCALDIR/standalone/pedigree')
    env['APPS_BASE'] = _expand('$LOCALDIR')

    env['UNPRIVILEGED_GID'] = '$UNPRIV_GID'
    env['UNPRIVILEGED_UID'] = '$UNPRIV_UID'

EOF

# Done. All set to go now.
echo "Standalone preparation is now complete."