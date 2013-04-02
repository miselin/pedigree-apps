#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

ARCH_TARGET="$ARCH_TARGET-pedigree" make posix > /dev/null 2>&1

