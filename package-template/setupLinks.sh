#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
## ADDME: check for link existence and rm the link

# Link updated files
## ADDME: add ln commands to link files into $CROSS_BASE

