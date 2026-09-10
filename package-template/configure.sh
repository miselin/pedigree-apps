#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --target=$ARCH_TARGET-pedigree \
             --bindir=/usr/bin --sysconfdir=/etc/$package \
             --prefix=/usr --libdir=/usr/lib --includedir=/usr/include \
             > /dev/null 2>&1
