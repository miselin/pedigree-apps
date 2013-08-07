#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

make $3 perl # > /dev/null 2>&1

