#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2"

make INSTALL_PREFIX="$OUTPUT_BASE/$package/$version/" install > /dev/null 2>&1

cd "$OUTPUT_BASE/$package/$version"

# Fix directory layout.
mv bin applications
mv lib libraries

