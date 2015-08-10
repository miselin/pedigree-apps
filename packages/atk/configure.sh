#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2"
mkdir -p build-atk && cd build-atk

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-sysroot=$CROSS_BASE --with-libiconv LDFLAGS="$LDFLAGS" \
             CPPFLAGS="$CPPFLAGS"
