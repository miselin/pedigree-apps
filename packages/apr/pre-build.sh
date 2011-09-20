#!/bin/bash

source "$1/environment.sh"

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

cd "$2"

# This is (hopefully) the Pedigree libtoolize in $PATH - it adds all our libtool
# files to the tree automatically.
libtoolize --copy -i -v -f > /dev/null 2>&1

# APR has a special libtool that uses apr_builddir instead of top_builddir, which
# is fine if we don't want to cross-compile. We do, and we go ahead and blow
# away APR's provided libtool, so we need to get that little change back. This
# patch does just that.
patch -p1 < $DIR/libtool.diff > /dev/null 2>&1

aclocal > /dev/null 2>&1

autoconf > /dev/null 2>&1

# Re-create aclocal.m4, referencing *our* libtool rather than the sytem
# libtool.
# aclocal -I ./build # -I ./libltdl -I ./libltdl/m4 # > /dev/null 2>&1

# Re-create the configure script now.
# autoconf # -I ./libltdl # > /dev/null 2>&1

# autoconf

cd "$2"

