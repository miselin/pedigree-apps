#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

# netsurf's build system doesn't know what CPPFLAGS is.
# It's also in need of hand holding to find things it builds, apparently.
CPPFLAGS="-I$2/prefix-framebuffer/include $CPPFLAGS"
export CFLAGS="$CPPFLAGS $CFLAGS"
export CXXFLAGS="$CPPFLAGS $CXXFLAGS"
export LDFLAGS
export LIBS

set -e

cd "$2"

# Remove -Werror from top-level subproject Makefiles
sed -i.bak s/\-Werror$//g src/*/Makefile

# We set CFLAGS in the environment, and netsurf overrides that.
sed -i.bak "s/CFLAGS \:=$/CFLAGS \?=/g" src/$package-$version/Makefile.defaults

# prepareCompiler hooks in ccache to all compiling, don't double up.
CC=$CC CXX=$CXX AR=$AR RANLIB=$RANLIB CCACHE="" \
make TARGET=framebuffer HOST=pedigree VQ= Q= PKG_CONFIG="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-pkg-config" NSFB_SDL_AVAILABLE="yes" NSFB_LINUX_AVAILABLE="no" NETSURF_USE_BMP="NO" NETSURF_USE_JPEG="NO" NETSURF_USE_MNG="NO" 

