#!/bin/bash

# usage: special.sh <download path> <path to environment.sh>

source ./package-info.sh
source $2/environment.sh

# Create directory tree.
mkdir pedigree-base
mkdir pedigree-base/libraries
mkdir pedigree-base/system

# Copy files, show what we're doing
echo "        -> libraries"
cp -R $PEDIGREE_BASE/images/base/libraries pedigree-base
echo "        -> fonts"
cp -R $PEDIGREE_BASE/images/base/system/fonts pedigree-base/system
echo "        -> keymaps"
cp -R $PEDIGREE_BASE/images/base/system/keymaps pedigree-base/keymaps

# Tar it up.
tar -czf $1/$package-$version.tar.gz pedigree-base

# Remove temporary directory
rm -rf pedigree-base

