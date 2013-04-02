#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"
set -e
mkdir -p build && cd build

../configure > /dev/null 2>&1

set +e
is_darwin=`uname -s | grep -i darwin`
set -e
pyext=""
if [ -z $is_darwin ]; then
    make python Parser/pgen > /dev/null 2>&1
else
    make python.exe Parser/pgen > /dev/null 2>&1
    pyext=".exe"
fi

mv python$pyext ../hostpython
mv Parser/pgen ../hostpgen

rm -rf *

mv ../hostpython ./
mkdir Parser
mv ../hostpgen ./Parser/

cd ..
autoreconf > /dev/null 2>&1

