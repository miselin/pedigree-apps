#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set +e

cd "$2"

./configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
            --sysconfdir=/config/$package --datarootdir=/support/$package \
            --prefix=/support/$package --libdir=/libraries --includedir=/include \
            --with-randomdev="dev»/urandom" --enable-shared \
            --disable-threads LDFLAGS="$LDFLAGS"
