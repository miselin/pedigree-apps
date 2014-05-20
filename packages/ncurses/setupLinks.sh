#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
ln -sf $BASE/libraries/libncurses.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libncurses.so $CROSS_BASE/lib/
ln -sf $BASE/libraries/libncurses_g.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libform.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libform.so $CROSS_BASE/lib/
ln -sf $BASE/libraries/libform_g.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libmenu.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libmenu.so $CROSS_BASE/lib/
ln -sf $BASE/libraries/libmenu_g.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libpanel.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libpanel_g.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libpanel.so $CROSS_BASE/lib/
ln -sf $BASE/libraries/libtinfo.a $CROSS_BASE/lib/
ln -sf $BASE/libraries/libtinfo.so $CROSS_BASE/lib/

ln -sf $BASE/include $CROSS_BASE/include/ncurses

