#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2/pup-build"

make DESTDIR="$OUTPUT_BASE/$package/$version/" install

