#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

ln -svf $BASE/libraries/*.so $CROSS_BASE/lib/
ln -svf $BASE/libraries/*.a $CROSS_BASE/lib/
ln -svf $BASE/include/*.h $CROSS_BASE/include/

