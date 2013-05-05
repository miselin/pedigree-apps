#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libpixman-1.a ]] && rm $CROSS_BASE/lib/libpixman-1.a
[[ -e $CROSS_BASE/lib/libpixman-1.so ]] && rm $CROSS_BASE/lib/libpixman-1.so
[[ -e $CROSS_BASE/include/pixman-1 ]] && rm $CROSS_BASE/include/pixman-1

ln -s $BASE/libraries/libpixman-1.a $CROSS_BASE/lib/libpixman-1.a
ln -s $BASE/libraries/libpixman-1.so $CROSS_BASE/lib/libpixman-1.so

ln -s $BASE/include/pixman-1 $CROSS_BASE/include/pixman-1

