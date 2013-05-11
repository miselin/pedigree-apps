#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libcrypto.a ]] && rm $CROSS_BASE/lib/libcrypto.a
[[ -e $CROSS_BASE/lib/libcrypto.so ]] && rm $CROSS_BASE/lib/libcrypto.so
[[ -e $CROSS_BASE/lib/libssl.a ]] && rm $CROSS_BASE/lib/libssl.a
[[ -e $CROSS_BASE/lib/libssl.so ]] && rm $CROSS_BASE/lib/libssl.so
[[ -e $CROSS_BASE/include/openssl ]] && rm $CROSS_BASE/include/openssl

ln -s $BASE/libraries/libcrypto.a $CROSS_BASE/lib/libcrypto.a
ln -s $BASE/libraries/libssl.a $CROSS_BASE/lib/libssl.a
ln -s $BASE/libraries/libcrypto.so $CROSS_BASE/lib/libcrypto.so
ln -s $BASE/libraries/libssl.so $CROSS_BASE/lib/libssl.so

ln -s $BASE/include/openssl $CROSS_BASE/include/openssl

