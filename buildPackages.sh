#!/bin/bash

BASEDIR=$PWD

cd packages

# Put any dependent libraries before the applications that need them
# TODO: sort.
DIRS="libgmp libmpfr libmpc zlib curl coreutils diffutils bsdtar newlib bash m4 nasm gnumake binutils gcc dosbox prboom"

for f in $DIRS; do
    echo
    echo "---------- Building in directory $f ----------"
    echo
    ENVPATH=$BASEDIR $f/build.sh
    
    # Packages that provide headers or libraries that other packages need are
    # required to provide a "setupLinks.sh" script that automatically creates
    # links in the cross-compiler for the package (as packages may have different
    # layouts)
    if [ -e $f/setupLinks.sh ]; then    
        echo "    -> Linking to cross-compiler, future packages depend on '$f'"
        ENVPATH=$BASEDIR ./$f/setupLinks.sh
    fi
done

cd $BASEDIR

