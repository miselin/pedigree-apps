#!/bin/bash

packagedir=$1

shift

oldwd=$PWD

if [ ! -e "packages/$packagedir" ]; then
    echo "The package '$packagedir' does not exist." 1>&2
    exit 2
fi

if [ -e "packages/$packagedir/package.py" ]; then
    if grep -Fq "TemplatePackage" "packages/$packagedir/package.py"; then
        echo "Converting $packagedir to package.py system..." 1>&2
    else
        echo "Skipping package $packagedir, it's already been converted." 1>&2
        exit 1
    fi
fi

if [ -z $ENVPATH ]; then
    ENVPATH=$PWD
fi

if [ ! -e $ENVPATH/environment.sh ]; then
    echo "no environment.sh found"
    exit 2
fi

cd ./packages/$packagedir

bz2="no"
xz="no"
source ./package-info.sh

PACKAGE_NAME=$package
PACKAGE_VERSION=$version

if [ "x$urlpackage" != "x" ]; then
    # Various packages have a urlpackage variable.
    package=$urlpackage
fi

TABIFY="        "

PACKAGE_URL=$url
PACKAGE_URL=$(echo $PACKAGE_URL | sed "s/$package/%(package)s/g" - )
PACKAGE_URL=$(echo $PACKAGE_URL | sed "s/$version/%(version)s/g" - )

if [ $bz2 == "yes" ]; then
    TARBALL_FORMAT="bz2"
elif [ $xz == "yes" ]; then
    TARBALL_FORMAT="xz"
else
    TARBALL_FORMAT="gz"
fi

patchfiles=`find $SOURCE_BASE/$package/patches -maxdepth 1 -name "*.diff" 2>/dev/null`
versioned_patchfiles=`find $SOURCE_BASE/$package/patches/$version -maxdepth 1 -name "*.diff" 2>/dev/null`

PACKAGE_PATCHES="["
for patch in $patchfiles $versioned_patchfiles; do
    PACKAGE_PATCHES="$PACKAGE_PATCHES'$patch', "
done
PACKAGE_PATCHES=$(echo "$PACKAGE_PATCHES" | sed 's/, $//' - )]

scripts="./pre-build.sh ./configure.sh ./build.sh ./install.sh ./setupLinks.sh"
phases=( "Pre-build" "Configure" "Build" "Install" "Symlinks" )

PREBUILD=
CONFIGURE=
BUILD=
INSTALL=

if [ -e "./pre-build.sh" ]; then
    grep -q "libtoolize" "./pre-build.sh" && PREBUILD="$PREBUILD\n${TABIFY}steps.libtoolize(srcdir, env)"
    grep -qe "(aclocal|autoconf)" "./pre-build.sh" && PREBUILD="$PREBUILD\n${TABIFY}steps.autoconf(srcdir, env)"
    grep -q "autoreconf" "./pre-build.sh" && PREBUILD="$PREBUILD\n${TABIFY}steps.autoreconf(srcdir, env)"
fi

if [ -e "./configure.sh" ]; then
    grep -q "configure" "./configure.sh" && CONFIGURE="$CONFIGURE\n${TABIFY}steps.run_configure(self, srcdir, env)"
fi

if [ -e "./build.sh" ]; then
    grep -q "make" "./build.sh" && BUILD="$BUILD\n${TABIFY}steps.make(srcdir, env)"
fi

if [ -e "./install.sh" ]; then
    grep -q "make.*install" "./install.sh" && INSTALL="$INSTALL\n${TABIFY}steps.make(srcdir, env, target='install')"
fi

if [ "x$PREBUILD" = "x" ]; then
    PREBUILD="\n${TABIFY}pass"
fi

if [ "x$CONFIGURE" = "x" ]; then
    CONFIGURE="$CONFIGURE\n${TABIFY}raise Exception('conversion had no idea how to configure')"
fi

if [ "x$BUILD" = "x" ]; then
    BUILD="$BUILD\n${TABIFY}raise Exception('conversion had no idea how to build')"
fi

if [ "x$INSTALL" = "x" ]; then
    INSTALL="$INSTALL\n${TABIFY}raise Exception('conversion had no idea how to install')"
fi

export TARBALL_FORMAT
export PACKAGE_NAME
export PACKAGE_VERSION
export PACKAGE_PATCHES
export PACKAGE_URL
export PREBUILD=$(echo -e "$PREBUILD")
export CONFIGURE=$(echo -e "$CONFIGURE")
export BUILD=$(echo -e "$BUILD")
export INSTALL=$(echo -e "$INSTALL")

# Expand variables in the template.
echo 'cat <<EOF' >.tmp.sh
cat "$oldwd/package-template/package.py" >>.tmp.sh
echo 'EOF' >>.tmp.sh
/bin/bash .tmp.sh >"./package.py"
rm -f .tmp.sh

PACKAGE_CLASS=$(echo $PACKAGE_NAME | sed 's/^\([A-Za-z]\)\([A-Za-z]\+\)/\U\1\L\2/')
PACKAGE_CLASS=$(echo $PACKAGE_CLASS | sed 's/[^A-Za-z]/_/g')
sed -i "s/TemplatePackage/${PACKAGE_CLASS}Package/g" "./package.py"

exit 0
