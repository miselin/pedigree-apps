#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libiconv.a ]] && rm $CROSS_BASE/lib/libiconv.a
[[ -e $CROSS_BASE/lib/libcharset.a ]] && rm $CROSS_BASE/lib/libcharset.a
[[ -e $CROSS_BASE/lib/libiconv.so ]] && rm $CROSS_BASE/lib/libiconv.so
[[ -e $CROSS_BASE/lib/libcharset.so ]] && rm $CROSS_BASE/lib/libcharset.so
[[ -e $CROSS_BASE/include/iconv.h ]] && rm $CROSS_BASE/include/iconv.h
[[ -e $CROSS_BASE/include/libcharset.h ]] && rm $CROSS_BASE/include/libcharset.h
[[ -e $CROSS_BASE/include/localcharset.h ]] && rm $CROSS_BASE/include/localcharset.h

ln -s $BASE/libraries/libiconv.a $CROSS_BASE/lib/libiconv.a
ln -s $BASE/libraries/libcharset.a $CROSS_BASE/lib/libcharset.a
ln -s $BASE/libraries/libiconv.so $CROSS_BASE/lib/libiconv.so
ln -s $BASE/libraries/libcharset.so $CROSS_BASE/lib/libcharset.so

ln -s $BASE/include/iconv.h $CROSS_BASE/include/iconv.h
ln -s $BASE/include/libcharset.h $CROSS_BASE/include/libcharset.h
ln -s $BASE/include/localcharset.h $CROSS_BASE/include/localcharset.h

