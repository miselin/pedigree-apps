#!/bin/bash

package=gmp
version=5.0.1

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libgmp.a ]] && rm $CROSS_BASE/lib/libgmp.a
[[ -e $CROSS_BASE/lib/libgmp.so ]] && rm $CROSS_BASE/lib/libgmp.so
[[ -e $CROSS_BASE/include/gmp.h ]] && rm $CROSS_BASE/include/gmp.h

ln -s $BASE/libraries/libgmp.a $CROSS_BASE/lib/libgmp.a
ln -s $BASE/libraries/libgmp.so $CROSS_BASE/lib/libgmp.so

# TODO: Find out why libgmp isn't using the --includedir directive!
ln -s $BASE/support/gmp/include/gmp.h $CROSS_BASE/include/gmp.h

