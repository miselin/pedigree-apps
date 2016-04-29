#!/bin/bash

# Standalone pedigree-apps prepare - builds a local Pedigree build and then
# writes out a local configuration that uses that build directly. This allows
# the pedigree-apps build to be completely self-contained.

# TODO(miselin): assumes running on a build slave
# TODO(miselin): assumes Debian as the host system

# Abort the build immediately if anything goes wrong.
set -e

UNPRIV_UID=$(id -u $USER)
UNPRIV_GID=$(id -g $USER)

LOCALDIR="$PWD"

# Make sure we're in the pedigree-apps root.
if [ ! -e "./buildPackages.py" ]; then
    echo "Must be run in pedigree-apps root directory." 1>&2
    exit 1
fi

# Grab architecture for building.
EASY_BUILD_TARGET=$1
if [ "x$EASY_BUILD_TARGET" = "x" ]; then
    EASY_BUILD_TARGET=x64
fi

echo "Standalone build for target $EASY_BUILD_TARGET"

# Quick hack to move along existing standalone builds.
if [ -d standalone ]; then
    mv standalone standalone-x64
fi
mkdir -p standalone-$EASY_BUILD_TARGET && cd standalone-$EASY_BUILD_TARGET

# Create a Python virtual environment if one doesn't exist yet.
# NOTE: if we're already in one, don't bother (no need).
if [ "x$VIRTUAL_ENV" = "x" ]; then
    if [ ! -e "venv" ]; then
        virtualenv --system-site-packages venv
    fi
fi

# Grab Pedigree first.
if [ ! -e "pedigree" ]; then
    git clone --depth 1 https://github.com/miselin/pedigree.git
fi

# Go ahead and build it.
cd pedigree
git pull
rm -f .easy_os  # Make sure we retry downloading packages.

# Don't do custom behaviour on travis for the standalone build.
if [ "x$TRAVIS" != "x" ]; then
    cat <<EOF >./build-etc/travis.sh
#!/bin/bash
TRAVIS_OPTIONS="forcemtools=1 build_kernel=0 build_modules=0 build_configdb=0"
TRAVIS_OPTIONS="$TRAVIS_OPTIONS build_lgpl=1 build_apps=0 build_libs=1"
TRAVIS_OPTIONS="$TRAVIS_OPTIONS build_images=0"

EOF
fi
./easy_build_$EASY_BUILD_TARGET.sh noconfirm debian build_images=0
cd ..

# Create our local configuration, ready to ship.
cd ..
cat >local_environment.py <<EOF

import functools

from support.util import expand


def modify_environment(env):
    _expand = functools.partial(expand, env)
    env['PEDIGREE_BASE'] = _expand('$LOCALDIR/standalone-$EASY_BUILD_TARGET/pedigree')
    env['APPS_BASE'] = _expand('$LOCALDIR')
    env['CCACHE_TARGET_DIR'] = '/mnt/ram/ccache'

    env['UNPRIVILEGED_GID'] = '$UNPRIV_GID'
    env['UNPRIVILEGED_UID'] = '$UNPRIV_UID'

EOF

# Done. All set to go now.
echo "Standalone preparation is now complete."
