#!/bin/bash

package=
version=
url=

echo "Building $package ($version)..."

if [ -z $ENVPATH ]; then
    echo "ENVPATH not set, fixing" 1>&2
    ENVPATH=../..
fi

source $ENVPATH/environment.sh

export CFLAGS
export CXXFLAGS
export LDFLAGS

oldwd=$PWD

mkdir -p $BUILD_BASE
mkdir -p $DOWNLOAD_TEMP

rm -rf $BUILD_BASE/build-$package-$version
mkdir -p $BUILD_BASE/build-$package-$version
cd $BUILD_BASE/build-$package-$version

trap "rm -rf $BUILD_BASE/build-$package-$version; cd $oldwd; exit" INT TERM EXIT

echo "    -> Grabbing source..."

if [ ! -f $DOWNLOAD_TEMP/$package-$version.tar.gz ]; then
    wget $url -nv -O $DOWNLOAD_TEMP/$package-$version.tar.gz > /dev/null 2>&1
fi

cp $DOWNLOAD_TEMP/$package-$version.tar.gz .

tar -xzf $package-$version.tar.gz --strip 1
rm $package-$version.tar.gz

echo "    -> Patching where necessary"

patches=
patchfiles=`find $SOURCE_BASE/$package/patches -maxdepth 1 -name "*.diff"`
numpatches=`echo $patchfiles | wc -l`
if [ ! -z "$patchfiles" ]; then
    for f in $patchfiles; do
        echo "       (applying $f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f > /dev/null 2>&1
    done
    
    patches="#"
fi
patchfiles=`find $SOURCE_BASE/$package/patches/$version -maxdepth 1 -name "*.diff"`
numpatches=`echo $patchfiles | wc -l`
if [ ! -z "$patchfiles" ]; then
    for f in $patchfiles; do
        echo "       (applying $version/$f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f > /dev/null 2>&1
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

../configure --host=$ARCH_TARGET-pedigree --bindir=/applications \
             --sysconfdir=/config/$package --datarootdir=/support/$package \
             --prefix=/support/$package --libdir=/libraries --includedir=/include \
             > /dev/null 2>&1

echo "    -> Building..."

make $* > /dev/null 2>&1

echo "    -> Installing..."

make DESTDIR="$OUTPUT_BASE/$package/$version/" install > /dev/null 2>&1

echo "Package $package ($version) has been built, now registering in the package manager"

$PACKMAN_PATH makepkg --path $OUTPUT_BASE/$package/$version --repo $PACKMAN_REPO --name $package --ver $version
$PACKMAN_PATH regpkg --repo $PACKMAN_REPO --name $package --ver $version

cd $oldwd

rm -rf build-$package-$version

trap - INT TERM EXIT

