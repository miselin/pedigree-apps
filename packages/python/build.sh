#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build"

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen Parser/pgen $* > /dev/null 2>&1

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen python$pyext $* > /dev/null 2>&1

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython \
     HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -nostdlib -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree $* > /dev/null 2>&1

