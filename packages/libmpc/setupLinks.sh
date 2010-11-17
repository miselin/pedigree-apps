#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libmpc.a ]] && rm $CROSS_BASE/lib/libmpc.a
[[ -e $CROSS_BASE/include/mpc.h ]] && rm $CROSS_BASE/include/mpc.h

ln -s $BASE/libraries/libmpc.a $CROSS_BASE/lib/libmpc.a
ln -s $BASE/include/mpc.h $CROSS_BASE/include/mpc.h
