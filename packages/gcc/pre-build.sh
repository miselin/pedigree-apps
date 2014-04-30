#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# We use new GCC (4.8.2), but a newer libtool/autoconf/etc
# So stop GCC's build system complaining.
sed -i.bak '/dnl Ensure exactly this Autoconf version is used/d' ./config/override.m4
autoconf_version=`autoconf -V | grep "autoconf" | tr ' ' '\n' | tail -1`
sed -i.bak "s/2.64/${autoconf_version}/g" ./config/override.m4

LIBTOOL=$CROSS_BASE/bin/libtool
libtoolize -i -f --ltdl >/dev/null 2>&1
autoreconf --force -I ./libltdl >/dev/null 2>&1

# Fix libtool for libraries that need it fixed.
wd=`pwd`
for dir in . zlib libbacktrace libssp libffi libstdc++-v3; do
  [ ! -d $dir ] && continue
  cd $dir
  libtoolize -i -f --ltdl >/dev/null 2>&1
  [ -e ./configure.ac ] && autoreconf -i --force -I ./libltdl >/dev/null 2>&1
  cd $wd
done

