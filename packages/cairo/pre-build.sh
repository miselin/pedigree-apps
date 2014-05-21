#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

NOCONFIGURE=yes ./autogen.sh

