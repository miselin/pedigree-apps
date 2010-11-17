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

CC=$CC LD=$LD AR=$AR LDSHARED="$CC -shared -Wl,-shared -Wl,-soname,libz.so.1,--version-script,zlib.map" RANLIB=$RANLIB \
             ./configure --prefix=/support/$package \
             --libdir=/libraries --includedir=/include # \
             > /dev/null 2>&1

