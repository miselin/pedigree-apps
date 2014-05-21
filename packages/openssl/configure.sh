#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export AR
export RANLIB
export CFLAGS
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"

CC="$CC $CPPFLAGS" CXX="$CXX $CPPFLAGS" \
./Configure threads shared zlib-dynamic --prefix=/ --openssldir=/support/openssl pedigree-gcc

