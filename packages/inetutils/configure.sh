#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --libdir=/libraries --includedir=/include \
             --prefix=/support/$package --disable-threads \
             --disable-ifconfig --disable-logger --disable-rcp --disable-rlogin \
             --disable-rsh --disable-rexec \
             --disable-uucp \
             --disable-servers

