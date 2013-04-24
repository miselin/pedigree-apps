#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CPPFLAGS
export LDFLAGS
LIBS="$LIBS -lexpat -lfreetype"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-default-fonts=/system/fonts \
             > /dev/null 2>&1

