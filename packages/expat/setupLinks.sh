#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libexpat.a ]] && rm $CROSS_BASE/lib/libexpat.a
[[ -e $CROSS_BASE/include/expat.h ]] && rm $CROSS_BASE/include/expat.h
[[ -e $CROSS_BASE/include/expat_external.h ]] && rm $CROSS_BASE/include/expat_external.h

ln -s $BASE/libraries/libexpat.a $CROSS_BASE/lib/libexpat.a

ln -s $BASE/include/expat.h $CROSS_BASE/include/expat.h
ln -s $BASE/include/expat_external.h $CROSS_BASE/include/expat_external.h

