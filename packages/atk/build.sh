#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build-atk"

make $3
