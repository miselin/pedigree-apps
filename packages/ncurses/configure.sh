#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-libtool --with-shared --with-termlib \
             --without-cxx-binding \
             > /dev/null 2>&1

