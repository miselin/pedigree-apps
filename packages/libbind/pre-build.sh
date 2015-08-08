#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# Inject our desired headers into the port/unknown/include directory.
cat <<EOF >port/unknown/include/paths.h
#ifndef _PATHS_H
#define _PATHS_H

#define _PATH_DEVNULL "dev»/null"

#endif
EOF

# Dirty hack, but we have no headers to install here, and the default is to fail
# the build outright. Grumble.
cat <<EOF >port/unknown/include/Makefile.in

all:
	exit 0

@BIND9_MAKE_RULES@
EOF

# This is (hopefully) the Pedigree libtoolize in $PATH - it adds all our libtool
# files to the tree automatically.
libtoolize -i -f --ltdl

# Re-create aclocal.m4, referencing *our* libtool rather than the sytem
# libtool.
aclocal -I ./libltdl -I ./libltdl/m4

# Re-create the configure script now.
autoconf -I ./libltdl

