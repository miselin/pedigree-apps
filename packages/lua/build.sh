#!/bin/bash

package=lua
version=5.1.4
url="http://www.lua.org/ftp/$package-$version.tar.gz"

echo "Building $package ($version)..."

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

oldwd=$PWD

mkdir -p $BUILD_BASE
mkdir -p $DOWNLOAD_TEMP

rm -rf $BUILD_BASE/build-$package-$version
mkdir -p $BUILD_BASE/build-$package-$version
cd $BUILD_BASE/build-$package-$version

# trap "rm -rf $BUILD_BASE/build-$package-$version; cd $oldwd; exit" INT TERM EXIT

echo "    -> Grabbing source..."

if [ ! -f $DOWNLOAD_TEMP/$package-$version.tar.gz ]; then
    wget $url -nv -O $DOWNLOAD_TEMP/$package-$version.tar.gz
fi

cp $DOWNLOAD_TEMP/$package-$version.tar.gz .

tar -xzf $package-$version.tar.gz --strip 1
rm $package-$version.tar.gz

echo "    -> Patching where necessary"

patches=
patch_exists=$(ls $SOURCE_BASE/$package/patches/*.diff 2>/dev/null | wc -w)
if [ ! $patch_exists == 0 ]; then
    for f in $SOURCE_BASE/$package/patches/*.diff; do
        echo "       (applying $f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f
    done
    
    patches="#"
fi
patch_sub_exists=$(ls $SOURCE_BASE/$package/patches/$version/*.diff 2>/dev/null | wc -w)
if [ ! $patch_sub_exists == 0 ]; then
    for f in $SOURCE_BASE/$package/patches/$version/*.diff; do
        echo "       (applying $version/$f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f
    done
    
    patches="#"
fi

if [ -N $patches ]; then
    echo "       (no patches needed, hooray!)"
fi

cd $BUILD_BASE/build-$package-$version

set -e

echo "    -> Building..."

ARCH_TARGET="$ARCH_TARGET-pedigree" make posix $* # > /dev/null 2>&1

echo "    -> Installing..."

out="$OUTPUT_BASE/$package/$version"

make INSTALL_TOP="$out/" \
     INSTALL_BIN="$out/applications" \
     INSTALL_LIB="$out/libraries" \
     INSTALL_LMOD="$out/support/lua/share/5.1" \
     INSTALL_CMOD="$out/libraries/lua/5.1" \
     install # > /dev/null 2>&1

echo "Package $package ($version) has been built, now registering in the package manager"

$PACKMAN_PATH makepkg --path $OUTPUT_BASE/$package/$version --repo $PACKMAN_REPO --name $package --ver $version
$PACKMAN_PATH regpkg --repo $PACKMAN_REPO --name $package --ver $version

cd $oldwd

rm -rf $BUILD_BASE/build-$package-$version

trap - INT TERM EXIT

