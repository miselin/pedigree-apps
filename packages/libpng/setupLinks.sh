#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libpng.a ]] && rm $CROSS_BASE/lib/libpng.a
[[ -e $CROSS_BASE/lib/libpng.so ]] && rm $CROSS_BASE/lib/libpng.so
[[ -e $CROSS_BASE/include/png.h ]] && rm $CROSS_BASE/include/png.h
[[ -e $CROSS_BASE/include/pngconf.h ]] && rm $CROSS_BASE/include/pngconf.h
[[ -e $CROSS_BASE/include/pnglibconf.h ]] && rm $CROSS_BASE/include/pnglibconf.h
[[ -e $CROSS_BASE/include/libpng15 ]] && rm $CROSS_BASE/include/libpng15

echo "        * libpng.a"
ln -s $BASE/libraries/libpng15.a $CROSS_BASE/lib/libpng.a
echo "        * libpng.so"
ln -s $BASE/libraries/libpng15.so $CROSS_BASE/lib/libpng.so

echo "        * png.h"
ln -s $BASE/include/png.h $CROSS_BASE/include/png.h
echo "        * pngconf.h"
ln -s $BASE/include/pngconf.h $CROSS_BASE/include/pngconf.h
echo "        * pnglibconf.h"
ln -s $BASE/include/pnglibconf.h $CROSS_BASE/include/pnglibconf.h
echo "        * libpng15"
ln -s $BASE/include/libpng15 $CROSS_BASE/include/libpng15

