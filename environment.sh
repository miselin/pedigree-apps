# Environment definitions - modify to suit your own environment

ARCH_TARGET="i686"
APPS_BASE="/home/matthewi/pedigree-apps"
CROSS_BASE="/home/matthewi/pedigree-compiler"
OUTPUT_BASE="$APPS_BASE/newpacks/$ARCH_TARGET"
SOURCE_BASE="$APPS_BASE/packages"
DOWNLOAD_TEMP="/$APPS_BASE/downloads"
BUILD_BASE="$SOURCE_BASE/builds"

CC="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc"
CXX="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-g++"
CPP="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-cpp"
AS="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-as"
LD="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ld"
LIBS="-lm"

CFLAGS="-I$CROSS_BASE/include/curl -I$CROSS_BASE/include/SDL -O3 -D__PEDIGREE__"
CXXFLAGS=$CFLAGS

LDFLAGS="-L$CROSS_BASE/lib"

