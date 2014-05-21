#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"
set -e

autoreconf

mkdir -p build && cd build

../configure

set +e
is_darwin=`uname -s | grep -i darwin`
set -e
pyext=""
if [ -z $is_darwin ]; then
    make Parser/pgen python
else
    make Parser/pgen.exe python.exe
    pyext=".exe"
fi

mv python$pyext ../hostpython
mv Parser/pgen$pyext ../hostpgen

rm -rf *

mv ../hostpython ./
mkdir ./Parser
mv ../hostpgen ./Parser/

cd ..

