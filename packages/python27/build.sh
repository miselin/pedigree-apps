#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2/build"

make HOSTPYTHON="$2/build/hostpython" HOSTPGEN="$2/build/Parser/hostpgen" Parser/pgen

make HOSTPYTHON="$2/build/hostpython" HOSTPGEN="$2/build/Parser/hostpgen" python$pyext

make HOSTPYTHON="$2/build/hostpython" \
     HOSTPGEN="$2/build/Parser/hostpgen" \
     BLDSHARED="$ARCH_TARGET-pedigree-gcc -shared -Wl,-shared" \
     CROSS_COMPILING=yes MACHDEP=pedigree ARCH_BITS="$ARCH_BITS" ARCH_TARGET="$ARCH_TARGET" \
     XCOMPILE_SYSINCLUDE="$CROSS_BASE/$ARCH_TARGET-pedigree/include"
