#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set +e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --libdir=/libraries --includedir=/include \
             LDFLAGS="$LDFLAGS"

