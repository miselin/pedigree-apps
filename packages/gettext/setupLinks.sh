#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libgettextpo.a ]] && rm $CROSS_BASE/lib/libgettextpo.a
[[ -e $CROSS_BASE/lib/libintl.a ]] && rm $CROSS_BASE/lib/libintl.a
[[ -e $CROSS_BASE/include/libintl.h ]] && rm $CROSS_BASE/include/libintl.h
[[ -e $CROSS_BASE/include/gettext-po.h ]] && rm $CROSS_BASE/include/gettext-po.h

echo "        * libgettextpo.a"
ln -s $BASE/libraries/libgettextpo.a $CROSS_BASE/lib/libgettextpo.a
echo "        * libintl.a"
ln -s $BASE/libraries/libintl.a $CROSS_BASE/lib/libintl.a

echo "        * libintl.h"
ln -s $BASE/include/libintl.h $CROSS_BASE/include/libintl.h
echo "        * gettext-po.h"
ln -s $BASE/include/gettext-po.h $CROSS_BASE/include/gettext-po.h

