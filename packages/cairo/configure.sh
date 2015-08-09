#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2"

./configure --host=$ARCH_TARGET-pedigree --prefix=/support/$package \
            --libdir=/libraries --includedir=/include \
            --disable-xcb --disable-xlib --without-x \
            --disable-ps --disable-pdf --disable-gobject \
            --disable-full-testing --disable-static --enable-shared \
            CPPFLAGS="$CPPFLAGS -DCAIRO_NO_MUTEX=1" LDFLAGS="$LDFLAGS"

