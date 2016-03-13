#!/bin/bash

set -e

OLDWD=$PWD
cd $(dirname $(readlink -f $0))

python3 setup.py bdist_wheel

cd $OLDWD
./runwithenv.py sh -c 'mkdir -p $APPS_BASE/pup/package_repo'
./runwithenv.py sh -c 'cp pup/dist/pup*.whl $APPS_BASE/pup/package_repo/pup.whl'

