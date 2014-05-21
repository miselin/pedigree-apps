#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2"

out="$OUTPUT_BASE/$package/$version"

make INSTALL_TOP="$out" \
     INSTALL_BIN="$out/applications" \
     INSTALL_LIB="$out/libraries" \
     INSTALL_LMOD="$out/support/lua/share/5.1" \
     INSTALL_CMOD="$out/libraries/lua/5.1" \
     install

