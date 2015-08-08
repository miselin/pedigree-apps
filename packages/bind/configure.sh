#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export LDFLAGS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --libdir=/libraries --includedir=/include \
             --without-gssapi --without-openssl --with-randomdev="dev»/urandom" \
             --without-libxml2 --disable-threads --disable-backtrace \
             --disable-linux-caps BUILD_CC=gcc
