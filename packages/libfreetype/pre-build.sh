#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

NOCONFIGURE=yes sh ./autogen.sh > /dev/null 2>&1
