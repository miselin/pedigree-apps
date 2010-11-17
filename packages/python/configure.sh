#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2/build"

# Platform-specific modules/definitions (none for Pedigree)
mkdir -p $BUILD_BASE/build-$package-$version/Lib/plat-pedigree

../configure --host=$ARCH_TARGET-pedigree \
            --prefix=/support/$package/$shortversion \
            --bindir=/applications \
            --includedir=/include/python/$shortversion \
            --libdir=/libraries/python/$shortversion \
            --without-pydebug \
            > /dev/null 2>&1

