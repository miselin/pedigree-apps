#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libgmp.a ]] && rm $CROSS_BASE/lib/libgmp.a
[[ -e $CROSS_BASE/lib/libgmp.so ]] && rm $CROSS_BASE/lib/libgmp.so
[[ -e $CROSS_BASE/include/gmp.h ]] && rm $CROSS_BASE/include/gmp.h

echo "        * libgmp.a"
ln -s $BASE/libraries/libgmp.a $CROSS_BASE/lib/libgmp.a
echo "        * libgmp.so"
ln -s $BASE/libraries/libgmp.so $CROSS_BASE/lib/libgmp.so

# TODO: Find out why libgmp isn't using the --includedir directive!
echo "        * gmp.h"
ln -s $BASE/support/gmp/include/gmp.h $CROSS_BASE/include/gmp.h

