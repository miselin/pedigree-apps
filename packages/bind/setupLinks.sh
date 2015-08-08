#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

ln -sf $BASE/libraries/*.a $CROSS_BASE/lib/
ln -sf $BASE/include/* $CROSS_BASE/include/

