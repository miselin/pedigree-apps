#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
LIBS="$LIBS -lpthread"
export LIBS

set -e

cd "$2"

# perlcross is the only sane way to cross-compile perl.
curl 'http://download.berlios.de/perlcross/perl-5.16.3-cross-0.7.4.tar.gz/from_sourceforge' | tar -xz --strip-components=1

./configure --host=$ARCH_TARGET-pedigree --target=$ARCH_TARGET-pedigree --prefix=/support/$package \
            --mode=cross # \
            #

