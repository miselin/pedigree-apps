#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export LDFLAGS
export CPPFLAGS

set -e

cd "$2"
mkdir -p build && cd build

# We disable shared for now as the mesa build system seems to assume
# libtool versioning exists (even though it doesn't), and also because
# $ARCH_TARGET-pedigree-gcc -shared apparently doesn't actually do the
# right thing. Yay!
../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include --disable-werror \
             --enable-osmesa --with-osmesa-bits=8 --disable-dri --disable-glx \
             --with-dri-drivers=swrast --without-gallium-drivers --disable-egl \
             --disable-shared # > /dev/null 2>&1

