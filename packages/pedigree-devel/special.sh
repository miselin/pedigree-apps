#!/bin/bash

# usage: special.sh <download path> <path to environment.sh>

source ./package-info.sh
source $2/environment.sh

gcc_vers=`$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc -dumpversion`

# Create directory tree.
mkdir pedigree-devel
mkdir -p pedigree-devel/libraries/gcc/$ARCH_TARGET-pedigree/$gcc_vers

# Copy files, show what we're doing
echo "        -> crt*.o"
cp $PEDIGREE_BASE/build/kernel/crt*.o pedigree-devel/libraries/gcc/$ARCH_TARGET-pedigree/$gcc_vers/
echo "        -> development headers"
cp -R $PEDIGREE_BASE/src/subsys/posix/include pedigree-devel/support/gcc/include/

# Tar it up.
tar -czf $1/$package-$version.tar.gz pedigree-devel

# Remove temporary directory
rm -rf pedigree-devel

