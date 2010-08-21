#!/bin/bash

package=bash
version=4.1

echo "Building $package ($version)..."

source ../../environment.sh

export CFLAGS
export CXXFLAGS
export LDFLAGS
export LIBS

oldwd=$PWD

mkdir -p $BUILD_BASE
cd $BUILD_BASE

echo "    -> Patching where necessary"

rm -rf $BUILD_BASE/build-$package-$version

# trap "rm -rf $BUILD_BASE/build-$package-$version; cd $oldwd; exit" INT TERM EXIT

cp -r $SOURCE_BASE/$package/$version ./build-$package-$version

if [ -e $SOURCE_BASE/$package/patches/*.diff ]; then
    for f in $SOURCE_BASE/$package/patches/*.diff; do
        echo "       (applying $f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f
    done
else
    echo "       (no patches needed, hooray!)"
fi

mkdir -p $BUILD_BASE/build-$package-$version/build
cd $BUILD_BASE/build-$package-$version/build

set -e

echo "    -> Configuring..."

../configure --host=i686-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package \
             2>&1 > /dev/null

echo "    -> Building..."

make $* 2>&1 > /dev/null

echo "    -> Installing..."

make DESTDIR="$OUTPUT_BASE/$package/$version/" install 2>&1 > /dev/null

echo "Package $package ($version) has been built"

cd $oldwd

rm -rf build-$package-$version

trap - INT TERM EXIT

