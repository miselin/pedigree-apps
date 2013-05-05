#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

pushd conftools

# This is (hopefully) the Pedigree libtoolize in $PATH - it adds all our libtool
# files to the tree automatically.
libtoolize -i -f --ltdl > /dev/null 2>&1

cp libltdl/m4/libtool.m4 ./
cp libltdl/config/ltmain.sh ./

popd

# Re-create aclocal.m4, referencing *our* libtool rather than the sytem
# libtool.
aclocal -I ./conftools/libltdl -I ./conftools/libltdl/m4 > /dev/null 2>&1

# Re-create the configure script now.
autoconf -I ./conftools/libltdl > /dev/null 2>&1

