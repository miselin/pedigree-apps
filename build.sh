#!/bin/bash

# Architecture to build.
arch=$1

shift

packagedir=$1

shift

oldwd=$PWD

if [ ! -e "packages/$packagedir" ]; then
    echo "The package '$packagedir' does not exist." 1>&2
    exit 2
fi

if [ -z $ENVPATH ]; then
    ENVPATH=$PWD
fi

if [ -L $ENVPATH/environment.sh -o ! -e $ENVPATH/environment.sh ]; then
    rm -f $ENVPATH/environment.sh
    ln -s $ENVPATH/environment-$arch.sh $ENVPATH/environment.sh
else
    echo "environment.sh should not exist as anything other than a symlink, you should have environment-$arch.sh present instead."
fi
source $ENVPATH/environment.sh

cd ./packages/$packagedir

bz2="no"
source ./package-info.sh

trap "echo Build failed.; rm -rf $BUILD_BASE/build-$package-$version; cd $oldwd; exit 1" INT TERM EXIT

echo "Building $package ($version)..."

mkdir -p $BUILD_BASE
mkdir -p $DOWNLOAD_TEMP

# Handle the case where there's a special method for obtaining source.
# This script should obtain the source and tarball it, placing it into the path
# specified in $1 with the format $package-$version.tar.gz
if [ -e ./special.sh ]; then
    echo "    -> Running special method for obtaining source..."
    ./special.sh $DOWNLOAD_TEMP $ENVPATH
fi

rm -rf $BUILD_BASE/build-$package-$version
mkdir -p $BUILD_BASE/build-$package-$version
cd $BUILD_BASE/build-$package-$version

echo "    -> Grabbing/extracting source..."

if [ ! -e ./special.sh -a ! -f $DOWNLOAD_TEMP/$package-$version.tar.gz ]; then
    wget $url -nv -O $DOWNLOAD_TEMP/$package-$version.tar.gz > /dev/null 2>&1
fi

cp $DOWNLOAD_TEMP/$package-$version.tar.gz .

tarflags="-xzf"
if [ $bz2 == "yes" ]; then
    tarflags="-xjf"
fi
tar $tarflags $package-$version.tar.gz --strip 1
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

set -e

cd $ENVPATH/packages/$package
scripts="./pre-build.sh ./configure.sh ./build.sh ./install.sh ./setupLinks.sh"
phases=( "Pre-build" "Configure" "Build" "Install" "Symlinks" )

phaseNumber=0
for f in $scripts; do
    if [ -e $f ]; then
        echo "    -> "${phases[$phaseNumber]}
        $f "$ENVPATH" "$BUILD_BASE/build-$package-$version" $*
    fi
    
    let "phaseNumber += 1"
done

echo
echo "Package $package ($version) has been built, now registering in the package manager"

$PACKMAN_PATH makepkg --path $OUTPUT_BASE/$package/$version --repo $PACKMAN_REPO --name $package --ver $version --arch $arch
$PACKMAN_PATH regpkg --repo $PACKMAN_REPO --name $package --ver $version --arch $arch

cd $oldwd

set +e

rm -rf $BUILD_BASE/build-$package-$version

trap - INT TERM EXIT

