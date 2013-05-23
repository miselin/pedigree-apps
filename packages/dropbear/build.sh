#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build"

make PROGRAMS="dbclient" $3 > /dev/null 2>&1

