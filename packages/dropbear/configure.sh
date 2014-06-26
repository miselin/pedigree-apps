#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
CPPFLAGS="$CPPFLAGS -DIP_TOS=0x1000 -Du_int8_t=uint8_t -Du_int16_t=uint16_t -Du_int32_t=uint32_t "
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications --sbindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --disable-lastlog --disable-utmp --disable-wtmp

