#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

echo "No links yet!"

exit 0

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libfreetype.a ]] && rm $CROSS_BASE/lib/libfreetype.a
[[ -e $CROSS_BASE/include/ft2build.h ]] && rm $CROSS_BASE/include/ft2build.h
[[ -e $CROSS_BASE/include/freetype2 ]] && rm -r $CROSS_BASE/include/freetype2

echo "        * libfreetype.a"
ln -s $BASE/libraries/libfreetype.a $CROSS_BASE/lib/libfreetype.a

echo "        * ft2build.h"
ln -s $BASE/include/ft2build.h $CROSS_BASE/include/ft2build.h
echo "        * freetype2"
ln -s $BASE/include/freetype2 $CROSS_BASE/include/freetype2

