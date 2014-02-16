#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# We use old GCC (4.5.1), and a newer libtool/autoconf/etc
# So stop GCC's build system complaining.
sed -i.bak '/dnl Ensure exactly this Autoconf version is used/d' ./config/override.m4
autoconf_version=`autoconf -V | grep "autoconf" | tr ' ' '\n' | tail -1`
sed -i.bak "s/2.64/${autoconf_version}/g" ./config/override.m4

libtoolize -i -f --ltdl >/dev/null 2>&1

autoreconf -I ./libltdl >/dev/null 2>&1

cd "$2/libstdc++-v3"

libtoolize -i -f --ltdl >/dev/null 2>&1

autoreconf -I ./libltdl >/dev/null 2>&1

