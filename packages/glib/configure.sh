#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

export CFLAGS
export CPPFLAGS
export LDFLAGS
export LIBS="$LIBS -liconv"

set -e

cd "$2"
mkdir -p build-glib && cd build-glib

glib_cv_stack_grows=no glib_cv_uscore=no ac_cv_func_posix_getpwuid_r=no \
ac_cv_func_posix_getgrgid_r=no \
../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include \
             --with-sysroot=$CROSS_BASE --with-libiconv
