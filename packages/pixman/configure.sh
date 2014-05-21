#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
CPPFLAGS="$CPPFLAGS -DPIXMAN_NO_TLS "
export CPPFLAGS
export LDFLAGS
LIBS="$LIBS -lz"
export LIBS
export PNG_LIBS=" -lpng "

set -e

cd "$2"

./configure --host=$ARCH_TARGET-pedigree --prefix=/support/$package \
            --libdir=/libraries --includedir=/include --disable-gtk \
            --enable-shared

