#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

ln -sf $BASE/libraries/glib-2.0 $CROSS_BASE/lib/
ln -sf $BASE/libraries/*.so $CROSS_BASE/lib/
ln -sf $BASE/libraries/*.a $CROSS_BASE/lib/
ln -sf $BASE/include/* $CROSS_BASE/include/

