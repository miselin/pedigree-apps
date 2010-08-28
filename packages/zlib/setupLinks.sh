#!/bin/bash

package=zlib
version=1.2.5

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libz.a ]] && rm $CROSS_BASE/lib/libz.a
[[ -e $CROSS_BASE/include/zlib.h ]] && rm $CROSS_BASE/include/zlib.h
[[ -e $CROSS_BASE/include/zconf.h ]] && rm $CROSS_BASE/include/zconf.h

ln -s $BASE/libraries/libz.a $CROSS_BASE/lib/libz.a

ln -s $BASE/include/zlib.h $CROSS_BASE/include/zlib.h
ln -s $BASE/include/zconf.h $CROSS_BASE/include/zconf.h

