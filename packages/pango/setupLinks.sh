#!/bin/bash

exit 0

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libcurl.a ]] && rm $CROSS_BASE/lib/libcurl.a
[[ -e $CROSS_BASE/include/curl ]] && rm $CROSS_BASE/include/curl

ln -s $BASE/libraries/libcurl.a $CROSS_BASE/lib/libcurl.a

ln -s $BASE/include/curl $CROSS_BASE/include/curl

