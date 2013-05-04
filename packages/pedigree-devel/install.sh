#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

set -e

cd "$2"

mkdir -p $OUTPUT_BASE/$package/$version

for folder in *; do
    cp -r $folder $OUTPUT_BASE/$package/$version/
done

