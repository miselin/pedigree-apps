#!/bin/sh

set -x
set -e

if [ "x$PACKAGE" = "x" ]; then
    ./runtests.sh
else
    if [ "x$TARGET" = "x" ]; then
        TARGET="amd64"
    fi

    if [ "$TARGET" = "amd64" ]; then
        echo "building for amd64"
        EASY_BUILD_TARGET="x64"
    else
        echo "building for $TARGET"
        EASY_BUILD_TARGET="$TARGET"
    fi

    # Build the standalone Pedigree needed for package building.
    # NOTE: this also creates a virtualenv if we aren't already in one.
    ./standalone.sh $EASY_BUILD_TARGET

    # Build the specified package.
    ./buildPackages.sh "$TARGET" --only-depends "$PACKAGE"
fi
