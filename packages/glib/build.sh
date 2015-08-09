#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build-glib"

make $3
