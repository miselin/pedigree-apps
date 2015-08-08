#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libharfbuzz.a ]] && rm $CROSS_BASE/lib/libharfbuzz.a
[[ -e $CROSS_BASE/lib/libharfbuzz.so ]] && rm $CROSS_BASE/lib/libharfbuzz.so
[[ -e $CROSS_BASE/include/harfbuzz ]] && rm $CROSS_BASE/include/harfbuzz

ln -s $BASE/libraries/libharfbuzz.a $CROSS_BASE/lib/libharfbuzz.a
ln -s $BASE/libraries/libharfbuzz.so $CROSS_BASE/lib/libharfbuzz.so

ln -s $BASE/include/harfbuzz $CROSS_BASE/include/harfbuzz

