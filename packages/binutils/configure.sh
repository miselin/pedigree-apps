#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

CFLAGS="$CFLAGS $CPPFLAGS"
CXXFLAGS="$CXXFLAGS $CPPFLAGS"

export CFLAGS
export CXXFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"

sed -i.bak -e 's/@colophon/@@colophon/' -e 's/doc@cygnus.com/doc@@cygnus.com/' bfd/doc/bfd.texinfo

mkdir -p build && cd build

# XXX: --disable-werror is needed because of an issue with rlimit().

../configure --host=$ARCH_TARGET-pedigree --target=$ARCH_TARGET-pedigree \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include --bindir=/applications \
             --disable-werror \
             > /dev/null 2>&1
