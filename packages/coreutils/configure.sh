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

#### TODO: port openssl for crypt() so su actually builds! ####
../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --libdir=/libraries --includedir=/include --enable-no-install-program=stdbuf \
             --prefix=/support/$package --enable-threads \
             > /dev/null 2>&1
