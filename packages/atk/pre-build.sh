#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# This is (hopefully) the Pedigree libtoolize in $PATH - it adds all our libtool
# files to the tree automatically.
libtoolize -i -f --ltdl

autoreconf -i -f -I ./libltdl

