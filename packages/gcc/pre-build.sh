#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# We use old GCC (4.5.1), and a newer libtool/autoconf/etc
# So stop GCC's build system complaining.
sed -i.bak '/dnl Ensure exactly this Autoconf version is used/d' ./config/override.m4
autoconf_version=`autoconf -V | grep "autoconf" | tr ' ' '\n' | tail -1`
sed -i.bak "s/2.64/${autoconf_version}/g" ./config/override.m4

# Fix libtool for libraries that need it fixed.
wd=`pwd`
for dir in . libstdc++-v3; do
  [ ! -d $dir ] && continue
  cd $dir
  [ -e ./configure.ac ] && autoconf >/dev/null 2>&1
  cd $wd
done

