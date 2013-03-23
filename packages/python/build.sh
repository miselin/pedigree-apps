#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build"

echo Pgen
make HOSTPYTHON="$2/build/hostpython" HOSTPGEN="$2/build/Parser/hostpgen" Parser/pgen # > /dev/null 2>&1

echo Python
make HOSTPYTHON="$2/build/hostpython" HOSTPGEN="$2/build/Parser/hostpgen" python$pyext # > /dev/null 2>&1

echo Modules....
make HOSTPYTHON="$2/build/hostpython" \
     HOSTPGEN="$2/build/Parser/hostpgen" \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -nostdlib -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree ARCH_BITS="$ARCH_BITS" ARCH_TARGET="$ARCH_TARGET" \
     XCOMPILE_SYSINCLUDE="$CROSS_BASE/$ARCH_TARGET-pedigree/include" # > /dev/null 2>&1

exit 2
