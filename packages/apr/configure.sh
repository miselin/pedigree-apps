#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2"
mkdir -p pup-build && cd pup-build

../configure --host=$ARCH_TARGET-pedigree \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include --bindir=/applications \
             --cache-file=$BUILD_BASE/build-$package-$version/pedigree.cache \
             --enable-shared \
             > /dev/null 2>&1

