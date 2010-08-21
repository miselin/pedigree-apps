#!/bin/bash

# TransACT mirror, stupid SourceForge won't work with wget.
package=prboom
version=2.5.0
url="http://transact.dl.sourceforge.net/project/$package/$package%20stable/$version/$package-$version.tar.gz"

echo "Building $package ($version)..."

source ../../environment.sh

export CFLAGS
export CXXFLAGS
export LDFLAGS
LIBS="-lpedigree -lstdc++ $LIBS"
export LIBS

export CPP

oldwd=$PWD

mkdir -p $BUILD_BASE
mkdir -p $DOWNLOAD_TEMP

rm -rf $BUILD_BASE/build-$package-$version
mkdir -p $BUILD_BASE/build-$package-$version
cd $BUILD_BASE/build-$package-$version

trap "rm -rf $BUILD_BASE/build-$package-$version; cd $oldwd; exit" INT TERM EXIT

echo "    -> Grabbing source..."

if [ ! -f $DOWNLOAD_TEMP/$package-$version.tar.gz ]; then
    wget $url -nv -O $DOWNLOAD_TEMP/$package-$version.tar.gz
fi

cp $DOWNLOAD_TEMP/$package-$version.tar.gz .

tar -xzf $package-$version.tar.gz --strip 1
rm $package-$version.tar.gz

echo "    -> Patching where necessary"

patches=
if [ -e $SOURCE_BASE/$package/patches/*.diff ]; then
    for f in $SOURCE_BASE/$package/patches/*.diff; do
        echo "       (applying $f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f
    done
    
    patches="#"
fi
if [ -e $SOURCE_BASE/$package/patches/$version/*.diff ]; then
    for f in $SOURCE_BASE/$package/patches/$version/*.diff; do
        echo "       (applying $version/$f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f
    done
    
    patches="#"
fi

if [ -N $patches ]; then
    echo "       (no patches needed, hooray!)"
fi

mkdir -p $BUILD_BASE/build-$package-$version/build
cd $BUILD_BASE/build-$package-$version/build

set -e

echo "    -> Configuring..."

../configure --host=i686-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --libdir=/libraries --includedir=/include \
             --disable-gl --with-waddir=/support/$package/wads \
             2>&1 > /dev/null

echo "    -> Building..."

make $* 2>&1 > /dev/null

echo "    -> Installing..."

make DESTDIR="$OUTPUT_BASE/$package/$version/" install 2>&1 > /dev/null

echo "Package $package ($version) has been built"

cd $oldwd

rm -rf build-$package-$version

trap - INT TERM EXIT

