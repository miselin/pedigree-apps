#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
CPPFLAGS="$CPPFLAGS -DNO_IPV6=1"
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"

ac_cv_fread_reads_directories=no ac_cv_snprintf_returns_bogus=no \
./configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
            --sysconfdir=/config/$package --datarootdir=/support/$package \
            --prefix=/support/$package --libdir=/libraries --includedir=/include \
            --disable-ipv6 --without-tcltk
