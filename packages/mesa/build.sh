#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build"

make V=1 $3 > /dev/null 2>&1

