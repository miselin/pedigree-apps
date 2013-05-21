#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2/build"

make PROGRAMS="dbclient" DESTDIR="$OUTPUT_BASE/$package/$version/" install > /dev/null 2>&1

