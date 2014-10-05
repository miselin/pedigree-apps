#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

cd "$2"

# Remove -Werror from Makefile.am, Makefile.in
sed -i.bak 's/-Werror//g' Makefile.am
sed -i.bak 's/-Werror//g' Makefile.in

