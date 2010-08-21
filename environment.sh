# Environment definitions - modify to suit your own environment

ARCH_TARGET="i686"
CROSS_BASE="/home/matthewi/pedigree-compiler"
BUILD_BASE="/home/matthewi/pedigree-apps/source/builds"
OUTPUT_BASE="/home/matthewi/pedigree-apps/newpacks/$ARCH_TARGET"
SOURCE_BASE="/home/matthewi/pedigree-apps/source"

CC="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc"
CXX="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-g++"
CPP="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-cpp"
AS="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-as"
LD="$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ld"
LIBS="-lm"

CFLAGS="-I$CROSS_BASE/include/curl -I$CROSS_BASE/include/SDL -O3 -D__PEDIGREE__"
CXXFLAGS=$CFLAGS

LDFLAGS="-L$CROSS_BASE/lib"

