#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"
(uname -s | grep Darwin > /dev/null 2>&1 ) && echo "Cross-compiling Apache is not yet possible on Darwin hosts. Skipping build." && exit 2

export CFLAGS
export CXXFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --enable-layout=Pedigree \
             --cache-file=$BUILD_BASE/build-$package-$version/pedigree.cache \
             > /dev/null 2>&1
