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

mkdir -p $BUILD_BASE/build-$package-$version/build
cd $BUILD_BASE/build-$package-$version/build

set -e

echo "    -> Configuring (BOOTSTRAP)..."

../configure # > /dev/null 2>&1

echo "    -> Building (BOOTSTRAP)..."

make python Parser/pgen $* # > /dev/null 2>&1

echo "    -> Bootstrap $urlpackage $version built."

mv python hostpython
mv Parser/pgen Parser/hostpgen

make distclean

echo "    -> Re-creating configure script with Pedigree patches..."

cd ..
autoreconf
cd build

echo "    -> Configuring..."

../configure --host=$ARCH_TARGET-pedigree \
            --prefix=/support/$package/$shortversion \
            --bindir=/applications \
            --includedir=/include/python/$shortversion \
            --libdir=/libraries/python/$shortversion \
            --without-pydebug # \
#            > /dev/null 2>&1

echo "    -> Building (PGEN)..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen Parser/pgen $* # > /dev/null 2>&1

echo "    -> Building (PYTHON INTERPRETER)..."

make HOSTPYTHON=$BUILD_BASE/build-$package-$version/build/hostpython HOSTPGEN=$BUILD_BASE/build-$package-$version/build/Parser/hostpgen python $* # > /dev/null 2>&1

# TODO: finish me!

exit 1

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

