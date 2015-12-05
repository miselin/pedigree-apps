#!/bin/bash

# Distribute files within the given directory to the CDN.
SRCDIR=$1
TARGETDIR=$2

if [ "x$SRCDIR" = "x" ]; then
    echo "A source directory is required." 1>&2
    exit 1
fi

if [ "x$TARGETDIR" = "x" ]; then
    echo "A target directory is required." 1>&2
    exit 1
fi

# Perform the upload.
rsync -av --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r -e "ssh -i $KEYCDN_KEYPATH" \
    "$SRCDIR/" "miselin@rsync.keycdn.com:$TARGETDIR/"
