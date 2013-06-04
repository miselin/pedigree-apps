#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libstdc++.a ]] && rm $CROSS_BASE/lib/libstdc++.a
[[ -e $CROSS_BASE/lib/libstdc++.so ]] && rm $CROSS_BASE/lib/libstdc++.so
[[ -e $CROSS_BASE/lib/libsupc++.a ]] && rm $CROSS_BASE/lib/libsupc++.a
[[ -e $CROSS_BASE/include/c++ ]] && rm $CROSS_BASE/include/c++

ln -s $BASE/libraries/libstdc++.a $CROSS_BASE/lib/libstdc++.a
ln -s $BASE/libraries/libstdc++.so $CROSS_BASE/lib/libstdc++.so
ln -s $BASE/libraries/libsupc++.a $CROSS_BASE/lib/libsupc++.a

ln -s $BASE/support/gcc/include/c++/$version $CROSS_BASE/include/c++

