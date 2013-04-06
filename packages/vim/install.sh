#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2/src"
make DESTDIR="$OUTPUT_BASE/$package/$version/" install # > /dev/null 2>&1

