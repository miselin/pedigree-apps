#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CPPFLAGS
export LDFLAGS

set -e

cd "$2"
mkdir -p build && cd build

glib_cv_stack_grows=no \
../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-sysroot=$CROSS_BASE --help

