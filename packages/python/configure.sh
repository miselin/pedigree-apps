#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
# LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2/build"

# Platform-specific modules/definitions (none for Pedigree)
mkdir -p $2/Lib/plat-pedigree

../configure --host=$ARCH_TARGET-pedigree \
            --prefix=/support/$package/$shortversion \
            --bindir=/applications \
            --includedir=/include/python/$shortversion \
            --libdir=/support/$package/$shortversion/lib \
            --without-pydebug --with-threads \
            # > /dev/null 2>&1

