#!/bin/bash

DIRS=$(find . --maxdepth 1 -type d -name "*")
if [ -z $DIRS ]; then
    for f in ./packages/*; do
        echo
        echo "---------- Building in directory $f ----------"
        echo
        ENVPATH=$PWD $f/build.sh
    done
fi

