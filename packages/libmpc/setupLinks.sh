#!/bin/bash

package=mpc
version=0.8.2

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libmpc.a ]] && rm $CROSS_BASE/lib/libmpc.a
[[ -e $CROSS_BASE/include/mpc.h ]] && rm $CROSS_BASE/include/mpc.h

ln -s $BASE/libraries/libmpc.a $CROSS_BASE/lib/libmpc.a
ln -s $BASE/include/mpc.h $CROSS_BASE/include/mpc.h
