#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

CFLAGS="$CFLAGS $CPPFLAGS"
export CFLAGS
CXXFLAGS="$CXXFLAGS $CPPFLAGS"
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --target=$ARCH_TARGET-pedigree \
             --bindir=/applications --sysconfdir=/config/$package \
             --prefix=/support/$package --libdir=/libraries --includedir=/include \
             --oldincludedir=/include --with-newlib --enable-languages=c,c++ \
             --disable-libstdcxx-pch --enable-shared=libgcc,libstdc++ \
             --enable-sjlj-exceptions \
             > /dev/null 2>&1

