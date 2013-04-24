#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
LIBS="$LIBS -lz"
export LIBS
export PNG_LIBS=" -lpng "

set -e

cd "$2"

./configure --host=$ARCH_TARGET-pedigree --prefix=/support/$package \
            --libdir=/libraries --includedir=/include --disable-gtk \
            > /dev/null 2>&1

