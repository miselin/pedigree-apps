#/bin/bash

# Script to prepare a cross-compiler (base path given as the first argument) to
# build Pedigree programs without the Pedigree build system.
# You should have built Pedigree at least once before running this script in
# order to create crt0/crti/crtn and the libraries.

if test $# -lt 3 ; then
    echo "Usage: prepareCompiler.sh <path_to_xcompiler_base> <path_to_pedigree> <target_pair>" 1>&2
    exit
fi

if [ ! -e "$1" ] | [ ! -e "$2" ]; then
    echo "One of the specified paths does not exist" 1>&2
    exit
fi

GIVEN_CROSS_PATH=`echo "$1" | sed -e 's,\(.\)/$,\1,'`
GIVEN_PEDIGREE_PATH=`echo "$2" | sed -e 's,\(.\)/$,\1,'`
DESIRED_TARGET=$3

echo "Creating links..."

# CRT0/CRTi/CRTn
if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crt0.o" ]; then
    echo "    - crt0.o"
    ln -s "$GIVEN_PEDIGREE_PATH/build/kernel/crt0.o" "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crt0.o"
fi
if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crti.o" ]; then
    echo "    - crti.o"
    ln -s $GIVEN_PEDIGREE_PATH/build/kernel/crti.o "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crti.o"
fi
if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crtn.o" ]; then
    echo "    - crtn.o"
    ln -s "$GIVEN_PEDIGREE_PATH/build/kernel/crtn.o" "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/crtn.o"
fi

# libc/libm
if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/libc.so" ]; then
    echo "    - libc.so"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libc.so" "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/libc.so"
fi
if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/libm.so" ]; then
    echo "    - libm.so"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libm.so" "$GIVEN_CROSS_PATH/$DESIRED_TARGET/lib/libm.so"
fi

if [ ! -e "$GIVEN_CROSS_PATH/$DESIRED_TARGET/include" ]; then
    echo "    - POSIX headers"
    ln -s "$GIVEN_PEDIGREE_PATH/src/subsys/posix/include" "$GIVEN_CROSS_PATH/$DESIRED_TARGET/include"
fi

# libpedigree* and pthreads
if [ ! -e "$GIVEN_CROSS_PATH/lib/libpedigree.a" ]; then
    echo "    - libpedigree.a"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libpedigree.a" "$GIVEN_CROSS_PATH/lib/libpedigree.a"
fi
if [ ! -e "$GIVEN_CROSS_PATH/lib/libpedigree-c.a" ]; then
    echo "    - libpedigree-c.a"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libpedigree-c.a" "$GIVEN_CROSS_PATH/lib/libpedigree-c.a"
fi
if [ ! -e "$GIVEN_CROSS_PATH/include/pedigree-native" ]; then
    echo "    - libpedigree include files"
    ln -s "$GIVEN_PEDIGREE_PATH/src/subsys/native/include" "$GIVEN_CROSS_PATH/include/pedigree-native"
fi
if [ ! -e "$GIVEN_CROSS_PATH/lib/libpthread.a" ]; then
    echo "    - libpthread.a"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libpthread.a" "$GIVEN_CROSS_PATH/lib/libpthread.a"
fi

# SDL
if [ ! -e "$GIVEN_CROSS_PATH/lib/libSDL.a" ]; then
    echo "    - libSDL.a"
    ln -s "$GIVEN_PEDIGREE_PATH/build/libSDL.a" "$GIVEN_CROSS_PATH/lib/libSDL.a"
fi
if [ ! -e "$GIVEN_CROSS_PATH/include/SDL" ]; then
    echo "    - SDL include files"
    ln -s "$GIVEN_PEDIGREE_PATH/src/lgpl/SDL-1.2.14/include" "$GIVEN_CROSS_PATH/include/SDL"
fi

echo "Done!"

