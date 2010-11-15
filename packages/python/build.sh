#!/bin/bash

package=python
urlpackage=Python
version=2.6.6
shortversion=2.6
url="http://python.org/ftp/$package/$version/$urlpackage-$version.tgz"

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
patchfiles=`find $SOURCE_BASE/$package/patches -maxdepth 1 -name "*.diff" 2>/dev/null`
numpatches=`echo $patchfiles | wc -l`
if [ ! -z "$patchfiles" ]; then
    for f in $patchfiles; do
        echo "       (applying $f)"
        patch -p1 -d $BUILD_BASE/build-$package-$version/ < $f > /dev/null 2>&1
    done
    
    patches="#"
fi
patchfiles=`find $SOURCE_BASE/$package/patches/$version -maxdepth 1 -name "*.diff" 2>/dev/null`
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

echo "    -> Configuring (BOOTSTRAP)..."

../configure > /dev/null 2>&1

echo "    -> Building (BOOTSTRAP)..."

is_darwin=`uname -s | grep -i darwin`
pyext=""
if [ -z $is_darwin ]; then
    make python Parser/pgen $* > /dev/null 2>&1
else
    make python.exe Parser/pgen > /dev/null 2>&1
    pyext=".exe"
fi

echo "    -> Bootstrap $urlpackage $version built."

mv python$pyext hostpython
mv Parser/pgen Parser/hostpgen

make distclean > /dev/null 2>&1

echo "    -> Re-creating configure script with Pedigree patches..."

cd ..
autoreconf > /dev/null 2>&1
cd build

echo "    -> Configuring..."

# Platform-specific modules/definitions (none for Pedigree)
mkdir -p $BUILD_BASE/build-$package-$version/Lib/plat-pedigree

../configure --host=$ARCH_TARGET-pedigree \
            --prefix=/support/$package/$shortversion \
            --bindir=/applications \
            --includedir=/include/python/$shortversion \
            --libdir=/libraries/python/$shortversion \
            --without-pydebug \
            > /dev/null 2>&1

echo "    -> Building (PGEN)..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen Parser/pgen $* > /dev/null 2>&1

echo "    -> Building (PYTHON INTERPRETER)..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen python$pyext $* > /dev/null 2>&1

echo "    -> Building modules..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython \
     HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -nostdlib -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree $* > /dev/null 2>&1

echo "    -> Installing..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython \
     HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -nostdlib -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree \
     DESTDIR=$OUTPUT_BASE/$package/$version install $* \
     > /dev/null 2>&1

echo "Package $package ($version) has been built, now registering in the package manager"

$PACKMAN_PATH makepkg --path $OUTPUT_BASE/$package/$version --repo $PACKMAN_REPO --name $package --ver $version
$PACKMAN_PATH regpkg --repo $PACKMAN_REPO --name $package --ver $version

cd $oldwd

rm -rf $BUILD_BASE/build-$package-$version

trap - INT TERM EXIT

