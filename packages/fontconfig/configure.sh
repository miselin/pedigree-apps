#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

# Define CFLAGS/LIBS so pkg-config is not required.
FREETYPE_CFLAGS="$CPPFLAGS" \
EXPAT_LIBS="-lexpat" FREETYPE_LIBS="-lfreetype -lz" \
../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-default-fonts=/system/fonts --enable-shared \
             > /dev/null 2>&1

