#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# Force one job as OpenSSL's build system doesn't work in parallel very well.
# This will override anything set in $MAKEFLAGS.
make -j1 $3 > /dev/null 2>&1

