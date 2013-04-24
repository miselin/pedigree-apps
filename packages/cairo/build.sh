#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

echo -e "ign:\n\t@echo '<ignored>'\nall: ign\ninstall: ign\ndistclean: ign\nclean: ign\n\n" | tee test/Makefile > perf/Makefile

make $3 > /dev/null 2>&1

