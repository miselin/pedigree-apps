#!/bin/bash

package=binutils
version=2.19
url="http://ftp.gnu.org/gnu/$package/$package-$version.tar.gz"

echo "Building $package ($version)..."

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

export CFLAGS
export CXXFLAGS
export LDFLAGS
export LIBS

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
        echo "       (applying $version:$f)"
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

../configure --host=$ARCH_TARGET-pedigree --target=$ARCH_TARGET-pedigree \
             --sysconfdir=/config/$package --prefix=/support/$package \
             --libdir=/libraries --includedir=/include --bindir=/applications \
             2>&1 > /dev/null

echo "    -> Building..."

make $* 2>&1 > /dev/null

echo "    -> Installing..."

make DESTDIR="$OUTPUT_BASE/$package/$version/" install 2>&1 > /dev/null

echo "Package $package ($version) has been built"

cd $oldwd

rm -rf $BUILD_BASE/build-$package-$version

trap - INT TERM EXIT
