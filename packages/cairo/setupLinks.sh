#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libcairo.a ]] && rm $CROSS_BASE/lib/libcairo.a
[[ -e $CROSS_BASE/include/cairo ]] && rm $CROSS_BASE/include/cairo

ln -s $BASE/libraries/libcairo.a $CROSS_BASE/lib/libcairo.a

ln -s $BASE/include/cairo $CROSS_BASE/include/cairo

