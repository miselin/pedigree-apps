#!/bin/bash

package=
version=

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Paths below under $BASE may be modified as needed for the directory layout for
# the built package.

# Remove existing files to force our updated version/link
# [[ -e $CROSS_BASE/lib/libabc.a ]] && rm $CROSS_BASE/lib/libabc.a

# Create links
# ln -s $BASE/libraries/libabc.a $CROSS_BASE/lib/libabc.a

