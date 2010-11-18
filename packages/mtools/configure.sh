#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CC
export LD
export CFLAGS
export CXXFLAGS
export LDFLAGS
LIBS="$LIBS -liconv -lpthread"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --cache-file=../pedigree.cache --disable-floppyd # \
             > /dev/null 2>&1

