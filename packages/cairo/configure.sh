#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
CPPFLAGS="$CPPFLAGS -DCAIRO_NO_MUTEX=1"
export CPPFLAGS
export LDFLAGS
export LIBS

set -e

cd "$2"

png_CFLAGS="" png_LIBS="-lpng" \
./configure --host=$ARCH_TARGET-pedigree --prefix=/support/$package \
            --libdir=/libraries --includedir=/include \
            --disable-xcb --disable-xlib --without-x \
            --disable-ps --disable-pdf --disable-gobject \
            --disable-full-testing --disable-static --enable-shared > /dev/null 2>&1

