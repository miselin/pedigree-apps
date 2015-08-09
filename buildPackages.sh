#!/bin/bash

BASEDIR=$PWD

# Pull out the architecture to build.
ARCH=$1
shift

# Please try and keep $DIRS sorted and categorised where possible.

# libtool gets its own category, as it needs to be run early
DIRS="$DIRS libtool"

# Put any dependent libraries before the applications that need them
DIRS="$DIRS zlib libiconv gettext libbind glib libgmp libmpfr libmpc ncurses"
DIRS="$DIRS curl expat pth libpng libfreetype fontconfig pixman readline"
DIRS="$DIRS harfbuzz"

# Cross-compilers for special libraries
DIRS="$DIRS binutils gcc"

# Utilities
DIRS="$DIRS bsdtar coreutils diffutils e2fsprogs grep gnumake gzip inetutils"
DIRS="$DIRS m4 nano sed wget gawk less"

# Secure
DIRS="$DIRS openssl dropbear"

# Games
DIRS="$DIRS dosbox prboom"

# Programming languages (non-GCC)
DIRS="$DIRS lua nasm python26 python27"

# Graphics stack
DIRS="$DIRS cairo mesa pango"

# Other applications
DIRS="$DIRS apache2 bind bash lynx mtools netsurf vim vttest git"

# Apache modules
DIRS="$DIRS "

# Pedigree-specific stuff
DIRS="$DIRS pedigree-base pedigree-devel"

: > $BASEDIR/status.log

rm -rf $BASEDIR/packages/builds/logs

for f in $DIRS; do
    echo
    echo "---------- Building '$f' ----------"
    echo
    $BASEDIR/build.sh $ARCH $f $*

    if [ $? == 0 ]; then
        out="Success."
    else
        out="Failed."
    fi

    echo
    echo "$f: $out"
    echo "$f: $out" >> $BASEDIR/status.log
    echo
done

cd $BASEDIR

