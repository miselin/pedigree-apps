#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libpth.a ]] && rm $CROSS_BASE/lib/libpth.a
[[ -e $CROSS_BASE/include/pth.h ]] && rm $CROSS_BASE/include/pth.h

ln -s $BASE/libraries/libpth.a $CROSS_BASE/lib/libpth.a

ln -s $BASE/include/pth.h $CROSS_BASE/include/pth.h

