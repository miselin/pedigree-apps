#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libncurses.a ]] && rm $CROSS_BASE/lib/libncurses.a
[[ -e $CROSS_BASE/lib/libncurses++.a ]] && rm $CROSS_BASE/lib/libncurses++.a
[[ -e $CROSS_BASE/lib/libncurses_g.a ]] && rm $CROSS_BASE/lib/libncurses_g.a
[[ -e $CROSS_BASE/lib/libform.a ]] && rm $CROSS_BASE/lib/libform.a
[[ -e $CROSS_BASE/lib/libform_g.a ]] && rm $CROSS_BASE/lib/libform_g.a
[[ -e $CROSS_BASE/lib/libmenu.a ]] && rm $CROSS_BASE/lib/libmenu.a
[[ -e $CROSS_BASE/lib/libmenu_g.a ]] && rm $CROSS_BASE/lib/libmenu_g.a
[[ -e $CROSS_BASE/lib/libpanel.a ]] && rm $CROSS_BASE/lib/libpanel.a
[[ -e $CROSS_BASE/lib/libpanel_g.a ]] && rm $CROSS_BASE/lib/libpanel_g.a

[[ -e $CROSS_BASE/include/ncurses ]] && rm -r $CROSS_BASE/include/ncurses

ln -s $BASE/libraries/libncurses.a $CROSS_BASE/lib/libncurses.a
ln -s $BASE/libraries/libncurses++.a $CROSS_BASE/lib/libncurses++.a
ln -s $BASE/libraries/libncurses_g.a $CROSS_BASE/lib/libncurses_g.a
ln -s $BASE/libraries/libform.a $CROSS_BASE/lib/libform.a
ln -s $BASE/libraries/libform_g.a $CROSS_BASE/lib/libform_g.a
ln -s $BASE/libraries/libmenu.a $CROSS_BASE/lib/libmenu.a
ln -s $BASE/libraries/libmenu_g.a $CROSS_BASE/lib/libmenu_g.a
ln -s $BASE/libraries/libpanel.a $CROSS_BASE/lib/libpanel.a
ln -s $BASE/libraries/libpanel_g.a $CROSS_BASE/lib/libpanel_g.a

ln -s $BASE/include $CROSS_BASE/include/ncurses

