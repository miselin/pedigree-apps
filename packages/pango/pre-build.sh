#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

libtoolize -i -f --ltdl

NOCONFIGURE=yes ./autogen.sh
