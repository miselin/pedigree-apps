# Environment definitions - modify to suit your own environment

ARCH_TARGET="x86_64"
PEDIGREE_BASE=""
APPS_BASE=""
CROSS_BASE="$PEDIGREE_BASE/pedigree-compiler"
OUTPUT_BASE="$APPS_BASE/newpacks/$ARCH_TARGET"
SOURCE_BASE="$APPS_BASE/packages"
DOWNLOAD_TEMP="$APPS_BASE/downloads"
BUILD_BASE="$SOURCE_BASE/builds"
PACKMAN_PATH="$APPS_BASE/pup/pup"
PACKMAN_REPO="$APPS_BASE/pup/package_repo"

CC="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc"
CXX="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc"
CPP="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-cpp"
AS="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-as"
LD="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc"
AR="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ar"
RANLIB="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ranlib"
LIBS="-lm"

ARCH_BITS="64"

CFLAGS="-O3 -m$ARCH_BITS -march=k8 -msse2 -D__PEDIGREE__"
CXXFLAGS=$CFLAGS

# Include directories for the preprocessor
CPPFLAGS="$CPPFLAGS -I$CROSS_BASE/include -I$CROSS_BASE/include/SDL -I$CROSS_BASE/include/ncurses"

LDFLAGS="-L$CROSS_BASE/lib -Wl,-rpath-link,$CROSS_BASE/lib"

if [ -d "$CROSS_BASE/bin" ] && [[ ":$PATH:" != *":$CROSS_BASE/bin:"* ]]; then
    PATH="$CROSS_BASE/bin:$PATH"
fi
