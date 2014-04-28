#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
rm -f $CROSS_BASE/lib/libcrypto.*
rm -f $CROSS_BASE/lib/libssl.*
[[ -e $CROSS_BASE/include/openssl ]] && rm $CROSS_BASE/include/openssl

ln -s $BASE/libraries/libcrypto.* $CROSS_BASE/lib/
ln -s $BASE/libraries/libssl.* $CROSS_BASE/lib/

ln -s $BASE/include/openssl $CROSS_BASE/include/openssl

