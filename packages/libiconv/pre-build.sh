#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

aclocal -I m4 -I srcm4 > /dev/null 2>&1
autoconf > /dev/null 2>&1

cd preload
aclocal -I ../m4 -I ../srcm4 > /dev/null 2>&1
autoconf > /dev/null 2>&1

cd ../libcharset
cp ../m4/libtool.m4 ./m4/libtool.m4
aclocal -I ../m4 -I ../srcm4 > /dev/null 2>&1
autoconf > /dev/null 2>&1

