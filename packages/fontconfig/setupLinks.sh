#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libfontconfig.a ]] && rm $CROSS_BASE/lib/libfontconfig.a
[[ -e $CROSS_BASE/lib/libfontconfig.so ]] && rm $CROSS_BASE/lib/libfontconfig.so
[[ -e $CROSS_BASE/include/fontconfig ]] && rm -r $CROSS_BASE/include/fontconfig

echo "        * libfontconfig.a"
ln -s $BASE/libraries/libfontconfig.a $CROSS_BASE/lib/libfontconfig.a
echo "        * libfontconfig.so"
ln -s $BASE/libraries/libfontconfig.so $CROSS_BASE/lib/libfontconfig.so

echo "        * fontconfig"
ln -s $BASE/include/fontconfig $CROSS_BASE/include/fontconfig

