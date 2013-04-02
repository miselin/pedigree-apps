#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2/build"

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython \
     HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -nostdlib -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree \
     DESTDIR=$OUTPUT_BASE/$package/$version install $* \
     > /dev/null 2>&1

