#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

CFLAGS=`echo $CFLAGS | sed s/-O3/-O1/`
export CFLAGS
CXXFLAGS=`echo $CXXFLAGS | sed s/-O3/-O1/`
export CXXFLAGS
export CPPFLAGS
export LDFLAGS
LIBS="-lSDL -lui -lz -lpedigree -lstdc++ $LIBS"
export LIBS

set -e

cd "$2"
mkdir -p build && cd build

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --disable-alsatest --disable-sdltest \
             --disable-opengl --enable-core-inline --enable-dynamic-core \
             --enable-dynrec --enable-fpu --enable-fpu-x86 --disable-unaligned-memory

