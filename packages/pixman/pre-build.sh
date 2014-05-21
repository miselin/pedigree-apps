#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# This is (hopefully) the Pedigree libtoolize in $PATH - it adds all our libtool
# files to the tree automatically.
libtoolize -i -f --ltdl

# Re-create aclocal.m4, referencing *our* libtool rather than the sytem
# libtool.
aclocal -I ./libltdl -I ./libltdl/m4

# Re-create the configure script now.
# autoconf -I ./libltdl

