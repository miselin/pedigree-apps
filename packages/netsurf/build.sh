#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

# netsurf's build system doesn't know what CPPFLAGS is.
# It's also in need of hand holding to find things it builds, apparently.
CPPFLAGS="-I$2/prefix-framebuffer/include -DNO_IPV6=1 $CPPFLAGS"
export CFLAGS="$CPPFLAGS $CFLAGS"
export CXXFLAGS="$CPPFLAGS $CXXFLAGS"
export LDFLAGS="$LDFLAGS -L$2/prefix-framebuffer/lib -Wl,--whole-archive -lnsfb -Wl,--no-whole-archive -lcss -ldom -lhubbub -lnsbmp -lnsgif -lparserutils -lrosprite -lsvgtiny -lwapcaplet -lcurl -liconv -lssl -lcrypto -lSDL -lpedigree -lstdc++ -lpthread"
export LIBS

set -e

cd "$2"

# Remove -Werror from top-level subproject Makefiles
sed -i.bak s/\-Werror$//g src/*/Makefile

# We set CFLAGS in the environment, and netsurf overrides that.
sed -i.bak "s/CFLAGS \:=$/CFLAGS \?=/g" src/$package-$version/Makefile.defaults

# We force the variable to say 'use SDL' to be set.
sed -i.bak "s/^.*pkg_config_package.*SDL.*$/NSFB_SDL_AVAILABLE \?= no/g" src/libnsfb*/Makefile
sed -i.bak "s/^.*pkg_config_package.*sdl.*CFLAGS.*$//g" src/libnsfb*/Makefile

# prepareCompiler hooks in ccache to all compiling, don't double up.
CC=$CC CXX=$CXX AR=$AR RANLIB=$RANLIB CCACHE="" \
make TARGET=framebuffer HOST=pedigree VQ= Q= PKG_CONFIG="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-pkg-config" NSFB_SDL_AVAILABLE="yes" NSFB_LINUX_AVAILABLE="no" NETSURF_USE_BMP="NO" NETSURF_USE_JPEG="NO" NETSURF_USE_MNG="NO" NETSURF_USE_GIF="NO" NETSURF_USE_LIBICONV_PLUG="NO" DESTDIR="$OUTPUT_BASE/$package/$version/" install

